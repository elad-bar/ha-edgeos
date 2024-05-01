from asyncio import sleep
from datetime import datetime
import logging
import sys
from typing import Callable

from homeassistant.components.device_tracker import ATTR_IP, ATTR_MAC
from homeassistant.components.homeassistant import SERVICE_RELOAD_CONFIG_ENTRY
from homeassistant.const import ATTR_STATE
from homeassistant.core import Event, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import (
    async_dispatcher_connect,
    async_dispatcher_send,
)
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from ..common.connectivity_status import ConnectivityStatus
from ..common.consts import (
    ACTION_ENTITY_SET_NATIVE_VALUE,
    ACTION_ENTITY_TURN_OFF,
    ACTION_ENTITY_TURN_ON,
    ADDRESS_LIST,
    API_RECONNECT_INTERVAL,
    ATTR_ACTIONS,
    ATTR_ATTRIBUTES,
    ATTR_IS_ON,
    ATTR_LAST_ACTIVITY,
    DHCP_SERVER_LEASED,
    DOMAIN,
    ENTITY_CONFIG_ENTRY_ID,
    HA_NAME,
    HEARTBEAT_INTERVAL,
    SIGNAL_API_STATUS,
    SIGNAL_DEVICE_ADDED,
    SIGNAL_INTERFACE_ADDED,
    SIGNAL_SYSTEM_ADDED,
    SIGNAL_SYSTEM_DISCOVERED,
    SIGNAL_WS_STATUS,
    SYSTEM_INFO_DATA_FW_LATEST_URL,
    SYSTEM_INFO_DATA_FW_LATEST_VERSION,
    WS_RECONNECT_INTERVAL,
)
from ..common.entity_descriptions import (
    ENTITY_DEVICE_MAPPING,
    PLATFORMS,
    IntegrationEntityDescription,
)
from ..common.enums import DeviceTypes, EntityKeys
from ..data_processors.base_processor import BaseProcessor
from ..data_processors.device_processor import DeviceProcessor
from ..data_processors.interface_processor import InterfaceProcessor
from ..data_processors.system_processor import SystemProcessor
from .config_manager import ConfigManager
from .rest_api import RestAPI
from .websockets import WebSockets

_LOGGER = logging.getLogger(__name__)


class Coordinator(DataUpdateCoordinator):
    """My custom coordinator."""

    _api: RestAPI
    _websockets: WebSockets | None
    _processors: dict[DeviceTypes, BaseProcessor] | None = None

    _data_mapping: dict[
        str,
        Callable[[IntegrationEntityDescription], dict | None]
        | Callable[[IntegrationEntityDescription, str], dict | None],
    ] | None
    _system_status_details: dict | None

    _last_update: float
    _last_heartbeat: float

    def __init__(self, hass, config_manager: ConfigManager):
        """Initialize my coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=config_manager.entry_title,
            update_interval=config_manager.update_entities_interval,
            update_method=self._async_update_data,
        )

        entry = config_manager.entry

        signal_handlers = {
            SIGNAL_API_STATUS: self._on_api_status_changed,
            SIGNAL_WS_STATUS: self._on_ws_status_changed,
            SIGNAL_SYSTEM_DISCOVERED: self._on_unit_discovered,
        }

        for signal in signal_handlers:
            handler = signal_handlers[signal]

            entry.async_on_unload(async_dispatcher_connect(hass, signal, handler))

        config_data = config_manager.config_data
        entry_id = config_manager.entry_id

        self._api = RestAPI(self.hass, config_data, entry_id)
        self._websockets = WebSockets(config_data, entry_id)

        self._config_manager = config_manager

        self._data_mapping = None

        self._last_update = 0
        self._last_heartbeat = 0

        self._can_load_components: bool = False
        self._unique_messages: list[str] = []

        self._system_processor = SystemProcessor(config_manager.config_data)
        self._device_processor = DeviceProcessor(config_manager.config_data)
        self._interface_processor = InterfaceProcessor(config_manager.config_data)

        self._discovered_objects = []

        self._processors = {
            DeviceTypes.SYSTEM: self._system_processor,
            DeviceTypes.DEVICE: self._device_processor,
            DeviceTypes.INTERFACE: self._interface_processor,
        }

    @property
    def api(self) -> RestAPI:
        api = self._api

        return api

    @property
    def websockets_data(self) -> dict:
        data = self._websockets.data

        return data

    @property
    def config_manager(self) -> ConfigManager:
        config_manager = self._config_manager

        return config_manager

    async def on_home_assistant_start(self, _event_data: Event):
        await self.initialize()

    async def initialize(self):
        self._build_data_mapping()

        entry = self.config_manager.entry
        await self.hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

        _LOGGER.info(f"Start loading {DOMAIN} integration, Entry ID: {entry.entry_id}")

        await self.async_config_entry_first_refresh()

        await self._api.initialize()

    async def terminate(self):
        await self._websockets.terminate()

    def get_debug_data(self) -> dict:
        config_data = self._config_manager.get_debug_data()

        data = {
            "config": config_data,
            "api": self._api.data,
            "websockets": self._websockets.data,
        }

        return data

    async def _on_api_status_changed(self, entry_id: str, status: ConnectivityStatus):
        if entry_id != self._config_manager.entry_id:
            return

        if status == ConnectivityStatus.Connected:
            await self._api.update()

            await self._websockets.update_api_data(self._api.data)

            await self._websockets.initialize()

        elif status in [ConnectivityStatus.Failed]:
            await self._websockets.terminate()

            await sleep(API_RECONNECT_INTERVAL.total_seconds())

            await self._api.initialize()

        elif status == ConnectivityStatus.InvalidCredentials:
            self.update_interval = None

    async def _on_ws_status_changed(self, entry_id: str, status: ConnectivityStatus):
        if entry_id != self._config_manager.entry_id:
            return

        if status in [ConnectivityStatus.Failed, ConnectivityStatus.NotConnected]:
            await self._websockets.terminate()

            await sleep(WS_RECONNECT_INTERVAL.total_seconds())

            await self._api.initialize()

    @callback
    def _on_system_discovered(self, entry_id: str) -> None:
        if entry_id == self.config_manager.entry_id:
            key = DeviceTypes.SYSTEM

            if key not in self._discovered_objects:
                self._discovered_objects.append(key)

                async_dispatcher_send(self.hass, SIGNAL_SYSTEM_ADDED, entry_id)

    def _on_device_discovered(self, device_mac: str) -> None:
        key = f"{DeviceTypes.DEVICE} {device_mac}"

        if key not in self._discovered_objects:
            self._discovered_objects.append(key)

            async_dispatcher_send(
                self.hass,
                SIGNAL_DEVICE_ADDED,
                self._config_manager.entry_id,
                device_mac,
            )

    def _on_interface_discovered(self, interface_name: str) -> None:
        key = f"{DeviceTypes.INTERFACE} {interface_name}"

        if key not in self._discovered_objects:
            self._discovered_objects.append(key)

            async_dispatcher_send(
                self.hass,
                SIGNAL_INTERFACE_ADDED,
                self._config_manager.entry_id,
                interface_name,
            )

    async def _async_update_data(self):
        """Fetch parameters from API endpoint.

        This is the place to pre-process the parameters to lookup tables
        so entities can quickly look up their parameters.
        """
        try:
            api_connected = self._api.status == ConnectivityStatus.Connected
            aws_client_connected = (
                self._websockets.status == ConnectivityStatus.Connected
            )

            is_ready = api_connected and aws_client_connected

            if is_ready:
                now = datetime.now().timestamp()

                if now - self._last_heartbeat >= HEARTBEAT_INTERVAL.total_seconds():
                    await self._websockets.send_heartbeat()

                    self._last_heartbeat = now

                if now - self._last_update >= self.config_manager.update_api_interval:
                    await self._api.update()

                    self._last_update = now

                for processor_type in self._processors:
                    processor = self._processors[processor_type]
                    processor.update(self._api.data, self._websockets.data)

                devices = self._device_processor.get_devices()
                interfaces = self._interface_processor.get_interfaces()

                for device_mac in devices:
                    self._on_device_discovered(device_mac)

                for interface_name in interfaces:
                    self._on_interface_discovered(interface_name)

            return {}

        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}")

    def _build_data_mapping(self):
        data_mapping = {
            EntityKeys.CPU_USAGE: self._get_cpu_usage_data,
            EntityKeys.RAM_USAGE: self._get_ram_usage_data,
            EntityKeys.FIRMWARE: self._get_firmware_data,
            EntityKeys.LAST_RESTART: self._get_last_restart_data,
            EntityKeys.UNKNOWN_DEVICES: self._get_unknown_devices_data,
            EntityKeys.LOG_INCOMING_MESSAGES: self._get_log_incoming_messages_data,
            EntityKeys.CONSIDER_AWAY_INTERVAL: self._get_consider_away_interval_data,
            EntityKeys.UPDATE_ENTITIES_INTERVAL: self._get_update_entities_interval_data,
            EntityKeys.UPDATE_API_INTERVAL: self._get_update_api_interval_data,
            EntityKeys.INTERFACE_CONNECTED: self._get_interface_connected_data,
            EntityKeys.INTERFACE_RECEIVED_DROPPED: self._get_interface_received_dropped_data,
            EntityKeys.INTERFACE_SENT_DROPPED: self._get_interface_sent_dropped_data,
            EntityKeys.INTERFACE_RECEIVED_ERRORS: self._get_interface_received_errors_data,
            EntityKeys.INTERFACE_SENT_ERRORS: self._get_interface_sent_errors_data,
            EntityKeys.INTERFACE_RECEIVED_PACKETS: self._get_interface_received_packets_data,
            EntityKeys.INTERFACE_SENT_PACKETS: self._get_interface_sent_packets_data,
            EntityKeys.INTERFACE_RECEIVED_RATE: self._get_interface_received_rate_data,
            EntityKeys.INTERFACE_SENT_RATE: self._get_interface_sent_rate_data,
            EntityKeys.INTERFACE_RECEIVED_TRAFFIC: self._get_interface_received_traffic_data,
            EntityKeys.INTERFACE_SENT_TRAFFIC: self._get_interface_sent_traffic_data,
            EntityKeys.INTERFACE_MONITORED: self._get_interface_monitored_data,
            EntityKeys.INTERFACE_STATUS: self._get_interface_status_data,
            EntityKeys.DEVICE_RECEIVED_RATE: self._get_device_received_rate_data,
            EntityKeys.DEVICE_SENT_RATE: self._get_device_sent_rate_data,
            EntityKeys.DEVICE_RECEIVED_TRAFFIC: self._get_device_received_traffic_data,
            EntityKeys.DEVICE_SENT_TRAFFIC: self._get_device_sent_traffic_data,
            EntityKeys.DEVICE_TRACKER: self._get_device_tracker_data,
            EntityKeys.DEVICE_MONITORED: self._get_device_monitored_data,
        }

        self._data_mapping = data_mapping

        _LOGGER.debug(f"Data retrieval mapping created, Mapping: {self._data_mapping}")

    def get_device_info(
        self,
        entity_description: IntegrationEntityDescription,
        item_id: str | None = None,
    ) -> DeviceInfo:
        device_type = ENTITY_DEVICE_MAPPING.get(entity_description.key)
        processor = self._processors[device_type]

        device_info = processor.get_device_info(item_id)

        return device_info

    def get_data(
        self,
        entity_description: IntegrationEntityDescription,
        monitor_id: str | None = None,
    ) -> dict | None:
        result = None

        try:
            handler = self._data_mapping.get(entity_description.key)

            if handler is None:
                _LOGGER.error(
                    f"Handler was not found for {entity_description.key}, Entity Description: {entity_description}"
                )

            else:
                if monitor_id is None:
                    result = handler(entity_description)

                else:
                    result = handler(entity_description, monitor_id)

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(
                f"Failed to extract data for {entity_description}, Error: {ex}, Line: {line_number}"
            )

        return result

    def get_device_action(
        self,
        entity_description: IntegrationEntityDescription,
        monitor_id: str | None,
        action_key: str,
    ) -> Callable:
        device_data = self.get_data(entity_description, monitor_id)

        actions = device_data.get(ATTR_ACTIONS)
        async_action = actions.get(action_key)

        return async_action

    @staticmethod
    def _get_date_time_from_timestamp(timestamp):
        result = datetime.fromtimestamp(timestamp)

        return result

    def _get_cpu_usage_data(self, _entity_description) -> dict | None:
        data = self._system_processor.get()

        result = {
            ATTR_STATE: data.cpu,
        }

        return result

    def _get_ram_usage_data(self, _entity_description) -> dict | None:
        data = self._system_processor.get()

        result = {
            ATTR_STATE: data.mem,
        }

        return result

    def _get_firmware_data(self, _entity_description) -> dict | None:
        data = self._system_processor.get()

        result = {
            ATTR_IS_ON: data.upgrade_available,
            ATTR_ATTRIBUTES: {
                SYSTEM_INFO_DATA_FW_LATEST_URL: data.upgrade_url,
                SYSTEM_INFO_DATA_FW_LATEST_VERSION: data.upgrade_version,
            },
        }

        return result

    def _get_last_restart_data(self, _entity_description) -> dict | None:
        data = self._system_processor.get()

        result = {ATTR_STATE: data.last_reset}

        return result

    def _get_unknown_devices_data(self, _entity_description) -> dict | None:
        leased_devices = self._device_processor.get_leased_devices()

        result = {
            ATTR_STATE: len(leased_devices.keys()),
            ATTR_ATTRIBUTES: {
                DHCP_SERVER_LEASED: leased_devices,
            },
        }

        return result

    def _get_log_incoming_messages_data(self, _entity_description) -> dict | None:
        result = {
            ATTR_IS_ON: self.config_manager.log_incoming_messages,
            ATTR_ACTIONS: {
                ACTION_ENTITY_TURN_ON: self._set_log_incoming_messages_enabled,
                ACTION_ENTITY_TURN_OFF: self._set_log_incoming_messages_disabled,
            },
        }

        return result

    def _get_consider_away_interval_data(self, _entity_description) -> dict | None:
        result = {
            ATTR_STATE: self.config_manager.consider_away_interval,
            ATTR_ACTIONS: {
                ACTION_ENTITY_SET_NATIVE_VALUE: self._set_consider_away_interval,
            },
        }

        return result

    def _get_update_entities_interval_data(self, _entity_description) -> dict | None:
        result = {
            ATTR_STATE: self.config_manager.update_entities_interval,
            ATTR_ACTIONS: {
                ACTION_ENTITY_SET_NATIVE_VALUE: self._set_update_entities_interval,
            },
        }

        return result

    def _get_update_api_interval_data(self, _entity_description) -> dict | None:
        result = {
            ATTR_STATE: self.config_manager.update_api_interval,
            ATTR_ACTIONS: {
                ACTION_ENTITY_SET_NATIVE_VALUE: self._set_update_api_interval,
            },
        }

        return result

    def _get_interface_connected_data(
        self, _entity_description, interface_name: str
    ) -> dict | None:
        interface = self._interface_processor.get_data(interface_name)

        result = {ATTR_IS_ON: interface.l1up}

        return result

    def _get_interface_received_dropped_data(
        self, _entity_description, interface_name: str
    ) -> dict | None:
        interface = self._interface_processor.get_data(interface_name)

        result = {ATTR_STATE: interface.received.dropped}

        return result

    def _get_interface_sent_dropped_data(
        self, _entity_description, interface_name: str
    ) -> dict | None:
        interface = self._interface_processor.get_data(interface_name)

        result = {ATTR_STATE: interface.sent.dropped}

        return result

    def _get_interface_received_errors_data(
        self, _entity_description, interface_name: str
    ) -> dict | None:
        interface = self._interface_processor.get_data(interface_name)

        result = {ATTR_STATE: interface.received.errors}

        return result

    def _get_interface_sent_errors_data(
        self, _entity_description, interface_name: str
    ) -> dict | None:
        interface = self._interface_processor.get_data(interface_name)

        result = {ATTR_STATE: interface.sent.errors}

        return result

    def _get_interface_received_packets_data(
        self, _entity_description, interface_name: str
    ) -> dict | None:
        interface = self._interface_processor.get_data(interface_name)

        result = {ATTR_STATE: interface.received.packets}

        return result

    def _get_interface_sent_packets_data(
        self, _entity_description, interface_name: str
    ) -> dict | None:
        interface = self._interface_processor.get_data(interface_name)

        result = {ATTR_STATE: interface.sent.packets}

        return result

    def _get_interface_received_rate_data(
        self, _entity_description, interface_name: str
    ) -> dict | None:
        interface = self._interface_processor.get_data(interface_name)

        result = {ATTR_STATE: interface.received.total}

        return result

    def _get_interface_sent_rate_data(
        self, _entity_description, interface_name: str
    ) -> dict | None:
        interface = self._interface_processor.get_data(interface_name)

        result = {ATTR_STATE: interface.sent.rate}

        return result

    def _get_interface_received_traffic_data(
        self, _entity_description, interface_name: str
    ) -> dict | None:
        interface = self._interface_processor.get_data(interface_name)

        result = {ATTR_STATE: interface.received.total}

        return result

    def _get_interface_sent_traffic_data(
        self, _entity_description, interface_name: str
    ) -> dict | None:
        interface = self._interface_processor.get_data(interface_name)

        result = {ATTR_STATE: interface.sent.total}

        return result

    def _get_interface_monitored_data(
        self, _entity_description, interface_name: str
    ) -> dict | None:
        state = self.config_manager.get_monitored_interface(interface_name)

        result = {
            ATTR_IS_ON: state,
            ATTR_ACTIONS: {
                ACTION_ENTITY_TURN_ON: self._set_interface_monitor_enabled,
                ACTION_ENTITY_TURN_OFF: self._set_interface_monitor_disabled,
            },
        }

        return result

    def _get_interface_status_data(
        self, _entity_description, interface_name: str
    ) -> dict | None:
        interface = self._interface_processor.get_data(interface_name)

        result = {
            ATTR_IS_ON: interface.up,
            ATTR_ATTRIBUTES: {
                ADDRESS_LIST: interface.address,
            },
            ATTR_ACTIONS: {
                ACTION_ENTITY_TURN_ON: self._set_interface_enabled,
                ACTION_ENTITY_TURN_OFF: self._set_interface_disabled,
            },
        }

        return result

    def _get_device_received_rate_data(
        self, _entity_description, device_mac: str
    ) -> dict | None:
        device = self._device_processor.get_data(device_mac)

        result = {ATTR_STATE: device.received.rate}

        return result

    def _get_device_sent_rate_data(
        self, _entity_description, device_mac: str
    ) -> dict | None:
        device = self._device_processor.get_data(device_mac)

        result = {ATTR_STATE: device.sent.rate}

        return result

    def _get_device_received_traffic_data(
        self, _entity_description, device_mac: str
    ) -> dict | None:
        device = self._device_processor.get_data(device_mac)

        result = {ATTR_STATE: device.received.total}

        return result

    def _get_device_sent_traffic_data(
        self, _entity_description, device_mac: str
    ) -> dict | None:
        device = self._device_processor.get_data(device_mac)

        result = {ATTR_STATE: device.sent.total}

        return result

    def _get_device_tracker_data(
        self, _entity_description, device_mac: str
    ) -> dict | None:
        device = self._device_processor.get_data(device_mac)
        consider_away_interval = self.config_manager.consider_away_interval
        now_ts = datetime.now().timestamp()
        seconds_since_last_activity = now_ts - device.last_activity

        is_on = consider_away_interval >= seconds_since_last_activity

        result = {
            ATTR_IS_ON: is_on,
            ATTR_ATTRIBUTES: {
                ATTR_LAST_ACTIVITY: device.last_activity,
                ATTR_IP: device.ip,
                ATTR_MAC: device.mac,
            },
        }

        return result

    def _get_device_monitored_data(
        self, _entity_description, device_mac: str
    ) -> dict | None:
        state = self.config_manager.get_monitored_device(device_mac)

        result = {
            ATTR_IS_ON: state,
            ATTR_ACTIONS: {
                ACTION_ENTITY_TURN_ON: self._set_device_monitor_enabled,
                ACTION_ENTITY_TURN_OFF: self._set_device_monitor_disabled,
            },
        }

        return result

    async def _set_interface_enabled(self, _entity_description, interface_name: str):
        _LOGGER.debug(f"Enable interface {interface_name}")
        interface = self._interface_processor.get_data(interface_name)

        await self._api.set_interface_state(interface, True)

    async def _set_interface_disabled(self, _entity_description, interface_name: str):
        _LOGGER.debug(f"Disable interface {interface_name}")
        interface = self._interface_processor.get_data(interface_name)

        await self._api.set_interface_state(interface, False)

    async def _set_interface_monitor_enabled(
        self, _entity_description, interface_name: str
    ):
        _LOGGER.debug(f"Enable monitoring for interface {interface_name}")

        await self._config_manager.set_monitored_interface(interface_name, True)

    async def _set_interface_monitor_disabled(
        self, _entity_description, interface_name: str
    ):
        _LOGGER.debug(f"Disable monitoring for interface {interface_name}")

        await self._config_manager.set_monitored_interface(interface_name, False)

    async def _set_device_monitor_enabled(self, _entity_description, device_mac: str):
        _LOGGER.debug(f"Enable monitoring for device {device_mac}")

        await self._config_manager.set_monitored_device(device_mac, True)

    async def _set_device_monitor_disabled(self, _entity_description, device_mac: str):
        _LOGGER.debug(f"Disable monitoring for device {device_mac}")

        await self._config_manager.set_monitored_device(device_mac, False)

    async def _set_log_incoming_messages_enabled(self, _entity_description):
        _LOGGER.debug("Enable log incoming messages")

        await self._config_manager.set_log_incoming_messages(True)

        await self._reload_integration()

    async def _set_log_incoming_messages_disabled(self, _entity_description):
        _LOGGER.debug("Disable log incoming messages")

        await self._config_manager.set_log_incoming_messages(False)

        await self._reload_integration()

    async def _set_consider_away_interval(self, _entity_description, value: int):
        _LOGGER.debug("Disable log incoming messages")

        await self._config_manager.set_consider_away_interval(value)

        await self._reload_integration()

    async def _set_update_entities_interval(self, _entity_description, value: int):
        _LOGGER.debug("Disable log incoming messages")

        await self._config_manager.set_update_entities_interval(value)

        await self._reload_integration()

    async def _set_update_api_interval(self, _entity_description, value: int):
        _LOGGER.debug("Disable log incoming messages")

        await self._config_manager.set_update_api_interval(value)

        await self._reload_integration()

    async def _reload_integration(self):
        data = {ENTITY_CONFIG_ENTRY_ID: self.config_manager.entry_id}

        await self.hass.services.async_call(HA_NAME, SERVICE_RELOAD_CONFIG_ENTRY, data)
