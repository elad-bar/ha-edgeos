"""
Support for HA manager.
"""
from __future__ import annotations

from asyncio import sleep
from datetime import datetime
import logging
import sys
from typing import Awaitable, Callable

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntityDescription,
)
from homeassistant.components.select import SelectEntityDescription
from homeassistant.components.sensor import SensorEntityDescription, SensorStateClass
from homeassistant.components.switch import SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import async_get as async_get_device_registry
from homeassistant.helpers.entity import EntityCategory, EntityDescription

from ...configuration.managers.configuration_manager import ConfigurationManager
from ...configuration.models.config_data import ConfigData
from ...core.helpers.enums import ConnectivityStatus
from ...core.managers.home_assistant import HomeAssistantManager
from ...core.models.entity_data import EntityData
from ..api.api import IntegrationAPI
from ..api.storage_api import StorageAPI
from ..api.websocket import IntegrationWS
from ..helpers.const import *
from ..helpers.enums import InterfaceHandlers
from ..models.edge_os_device_data import EdgeOSDeviceData
from ..models.edge_os_interface_data import EdgeOSInterfaceData
from ..models.edge_os_system_data import EdgeOSSystemData

_LOGGER = logging.getLogger(__name__)


class EdgeOSHomeAssistantManager(HomeAssistantManager):
    def __init__(self, hass: HomeAssistant):
        super().__init__(hass, DEFAULT_UPDATE_API_INTERVAL, DEFAULT_HEARTBEAT_INTERVAL)

        self._storage_api: StorageAPI = StorageAPI(self._hass)
        self._api: IntegrationAPI = IntegrationAPI(self._hass, self._api_data_changed, self._api_status_changed)
        self._ws: IntegrationWS = IntegrationWS(self._hass, self._ws_data_changed, self._ws_status_changed)
        self._config_manager: ConfigurationManager | None = None
        self._system: EdgeOSSystemData | None = None
        self._devices: dict[str, EdgeOSDeviceData] = {}
        self._devices_ip_mapping: dict[str, str] = {}
        self._interfaces: dict[str, EdgeOSInterfaceData] = {}
        self._can_load_components: bool = False
        self._unique_messages: list[str] = []

    @property
    def hass(self) -> HomeAssistant:
        return self._hass

    @property
    def api(self) -> IntegrationAPI:
        return self._api

    @property
    def ws(self) -> IntegrationWS:
        return self._ws

    @property
    def storage_api(self) -> StorageAPI:
        return self._storage_api

    @property
    def config_data(self) -> ConfigData:
        return self._config_manager.get(self.entry_id)

    @property
    def system_name(self):
        name = self.entry_title

        if self._system is not None and self._system.hostname is not None:
            name = self._system.hostname.upper()

        return name

    async def async_send_heartbeat(self):
        """ Must be implemented to be able to send heartbeat to API """
        await self.ws.async_send_heartbeat()

    async def _api_data_changed(self):
        if self.api.status == ConnectivityStatus.Connected:
            await self._extract_api_data()

    async def _ws_data_changed(self):
        if self.ws.status == ConnectivityStatus.Connected:
            await self._extract_ws_data()

    async def _api_status_changed(self, status: ConnectivityStatus):
        _LOGGER.info(f"API Status changed to {status.name}, WS Status: {self.ws.status.name}")
        if status == ConnectivityStatus.Connected:
            await self.api.async_update()

            if self.ws.status == ConnectivityStatus.NotConnected:
                log_incoming_messages = self.storage_api.log_incoming_messages
                await self.ws.update_api_data(self.api.data, log_incoming_messages)

                await self.ws.initialize(self.config_data)

        if status == ConnectivityStatus.Disconnected:
            if self.ws.status == ConnectivityStatus.Connected:
                await self.ws.terminate()

    async def _ws_status_changed(self, status: ConnectivityStatus):
        _LOGGER.info(f"WS Status changed to {status.name}, API Status: {self.api.status.name}")

        api_connected = self.api.status == ConnectivityStatus.Connected
        ws_connected = status == ConnectivityStatus.Connected
        ws_reconnect = status in [ConnectivityStatus.NotConnected, ConnectivityStatus.Failed]

        self._can_load_components = ws_connected

        if ws_reconnect and api_connected:
            await sleep(WS_RECONNECT_INTERVAL.total_seconds())

            await self.ws.initialize()

    async def async_component_initialize(self, entry: ConfigEntry):
        try:
            self._config_manager = ConfigurationManager(self._hass, self.api)
            await self._config_manager.load(entry)

            await self.storage_api.initialize(self.config_data)

            update_entities_interval = timedelta(seconds=self.storage_api.update_entities_interval)
            update_api_interval = timedelta(seconds=self.storage_api.update_api_interval)

            _LOGGER.info(f"Setting intervals, API: {update_api_interval}, Entities: {update_entities_interval}")
            self.update_intervals(update_entities_interval, update_api_interval)

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(f"Failed to async_component_initialize, error: {ex}, line: {line_number}")

    async def async_initialize_data_providers(self):
        await self.storage_api.initialize(self.config_data)

        updated = False

        if self._entry is not None:
            migration_data = {}
            entry_options = self._entry.options

            if entry_options is not None:
                for option_key in entry_options:
                    migration_data[option_key] = entry_options.get(option_key)

            if self._entry.data is not None:
                migration_data[STORAGE_DATA_UNIT] = self._entry.data.get(STORAGE_DATA_UNIT)

            updated = await self._update_configuration_data(migration_data)

        if updated:
            _LOGGER.info("Starting configuration migration")

            data = {}
            for key in self._entry.data.keys():
                if key != STORAGE_DATA_UNIT:
                    value = self._entry.data.get(key)
                    data[key] = value

            options = {}

            self._hass.config_entries.async_update_entry(self._entry,
                                                         data=data,
                                                         options=options)

            _LOGGER.info("Configuration migration completed, reloading integration")

            await self._reload_integration()

        else:
            await self.api.initialize(self.config_data)

    async def async_stop_data_providers(self):
        await self.api.terminate()

    async def async_update_data_providers(self):
        try:
            await self.api.async_update()

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(f"Failed to async_update_data_providers, Error: {ex}, Line: {line_number}")

    def register_services(self, entry: ConfigEntry | None = None):
        self._hass.services.async_register(DOMAIN,
                                           SERVICE_UPDATE_CONFIGURATION,
                                           self._update_configuration,
                                           SERVICE_SCHEMA_UPDATE_CONFIGURATION)

    def load_devices(self):
        if not self._can_load_components:
            return

        self._load_main_device()

        for unique_id in self._devices:
            device_item = self._get_device(unique_id)
            self._load_device_device(device_item)

        for unique_id in self._interfaces:
            interface_item = self._interfaces.get(unique_id)
            self._load_interface_device(interface_item)

    def load_entities(self):
        _LOGGER.debug("Loading entities")

        if not self._can_load_components:
            return

        is_admin = self._system.user_level == USER_LEVEL_ADMIN

        self._load_unit_select()
        self._load_unknown_devices_sensor()
        self._load_cpu_sensor()
        self._load_ram_sensor()
        self._load_uptime_sensor()
        self._load_firmware_upgrade_binary_sensor()
        self._load_log_incoming_messages_switch()

        for unique_id in self._devices:
            device_item = self._get_device(unique_id)

            if device_item.is_leased:
                continue

            self._load_device_monitor_switch(device_item)
            self._load_device_tracker(device_item)

            stats_data = device_item.get_stats()

            for stats_data_key in stats_data:
                stats_data_item = stats_data.get(stats_data_key)

                self._load_device_stats_sensor(device_item, stats_data_key, stats_data_item)

        for unique_id in self._interfaces:
            interface_item = self._interfaces.get(unique_id)

            if interface_item.handler == InterfaceHandlers.IGNORED:
                continue

            if is_admin and interface_item.handler == InterfaceHandlers.REGULAR:
                self._load_interface_status_switch(interface_item)

            else:
                self._load_interface_status_binary_sensor(interface_item)

            self._load_interface_monitor_switch(interface_item)
            self._load_interface_connected_binary_sensor(interface_item)

            stats_data = interface_item.get_stats()

            for stats_data_key in stats_data:
                stats_data_item = stats_data.get(stats_data_key)

                self._load_interface_stats_sensor(interface_item, stats_data_key, stats_data_item)

    def _get_device_name(self, device: EdgeOSDeviceData):
        return f"{self.system_name} Device {device.hostname}"

    def _get_interface_name(self, interface: EdgeOSInterfaceData):
        return f"{self.system_name} Interface {interface.name.upper()}"

    async def _extract_ws_data(self):
        try:
            await self.storage_api.debug_log_ws(self.ws.data)

            interfaces_data = self.ws.data.get(WS_INTERFACES_KEY, {})
            device_data = self.ws.data.get(WS_EXPORT_KEY, {})

            system_stats_data = self.ws.data.get(WS_SYSTEM_STATS_KEY, {})
            discovery_data = self.ws.data.get(WS_DISCOVER_KEY, {})

            self._update_system_stats(system_stats_data, discovery_data)

            for device_ip in device_data:
                device_item = self._get_device_by_ip(device_ip)
                stats = device_data.get(device_ip)

                if device_item is not None:
                    self._update_device_stats(device_item, stats)

            for name in interfaces_data:
                interface_item = self._interfaces.get(name)
                stats = interfaces_data.get(name)

                if interface_item is None:
                    interface_data = interfaces_data.get(name)
                    interface_item = self._extract_interface(name, interface_data)

                self._update_interface_stats(interface_item, stats)

            await self._log_ha_data()

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(f"Failed to extract WS data, Error: {ex}, Line: {line_number}")

    async def _extract_api_data(self):
        try:
            _LOGGER.debug("Extracting API Data")

            await self.storage_api.debug_log_api(self.api.data)

            data = self.api.data.get(API_DATA_SYSTEM, {})
            system_info = self.api.data.get(API_DATA_SYS_INFO, {})

            self._extract_system(data, system_info)

            self._extract_unknown_devices()

            self._extract_interfaces(data)
            self._extract_devices(data)

            warning_messages = []

            if not self._system.deep_packet_inspection:
                warning_messages.append("DPI (deep packet inspection) is turned off")

            if not self._system.traffic_analysis_export:
                warning_messages.append("Traffic Analysis Export is turned off")

            if len(warning_messages) > 0:
                warning_message = " and ".join(warning_messages)

                _LOGGER.warning(f"Integration will not work correctly since {warning_message}")

            await self._log_ha_data()
        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(f"Failed to extract API data, Error: {ex}, Line: {line_number}")

    async def _log_ha_data(self):
        messages = {}

        for key in WS_MESSAGES:
            message_counter = self._ws.data.get(key, 0)
            counter_name = key.replace(f"-{MESSAGES_COUNTER_SECTION.lower()}", "")

            messages[counter_name] = message_counter

        data = {
            API_DATA_SYSTEM: self._system,
            DEVICE_LIST: self._devices,
            API_DATA_INTERFACES: self._interfaces,
            MESSAGES_COUNTER_SECTION: messages
        }

        await self.storage_api.debug_log_ha(data)

    def _extract_system(self, data: dict, system_info: dict):
        try:
            system_details = data.get(API_DATA_SYSTEM, {})

            system_data = EdgeOSSystemData() if self._system is None else self._system

            system_data.hostname = system_details.get(SYSTEM_DATA_HOSTNAME)
            system_data.timezone = system_details.get(SYSTEM_DATA_TIME_ZONE)

            ntp: dict = system_details.get(SYSTEM_DATA_NTP, {})
            system_data.ntp_servers = ntp.get(SYSTEM_DATA_NTP_SERVER)

            offload: dict = system_details.get(SYSTEM_DATA_OFFLOAD, {})
            hardware_offload = EdgeOSSystemData.is_enabled(offload, SYSTEM_DATA_OFFLOAD_HW_NAT)
            ipsec_offload = EdgeOSSystemData.is_enabled(offload, SYSTEM_DATA_OFFLOAD_IPSEC)

            system_data.hardware_offload = hardware_offload
            system_data.ipsec_offload = ipsec_offload

            traffic_analysis: dict = system_details.get(SYSTEM_DATA_TRAFFIC_ANALYSIS, {})
            dpi = EdgeOSSystemData.is_enabled(traffic_analysis, SYSTEM_DATA_TRAFFIC_ANALYSIS_DPI)
            traffic_analysis_export = EdgeOSSystemData.is_enabled(traffic_analysis,
                                                                  SYSTEM_DATA_TRAFFIC_ANALYSIS_EXPORT)

            system_data.deep_packet_inspection = dpi
            system_data.traffic_analysis_export = traffic_analysis_export

            sw_latest = system_info.get(SYSTEM_INFO_DATA_SW_VER)
            fw_latest = system_info.get(SYSTEM_INFO_DATA_FW_LATEST, {})

            fw_latest_state = fw_latest.get(SYSTEM_INFO_DATA_FW_LATEST_STATE)
            fw_latest_version = fw_latest.get(SYSTEM_INFO_DATA_FW_LATEST_VERSION)
            fw_latest_url = fw_latest.get(SYSTEM_INFO_DATA_FW_LATEST_URL)

            system_data.upgrade_available = fw_latest_state == FW_LATEST_STATE_CAN_UPGRADE
            system_data.upgrade_url = fw_latest_url
            system_data.upgrade_version = fw_latest_version

            system_data.sw_version = sw_latest

            login_details = system_details.get(SYSTEM_DATA_LOGIN, {})
            users = login_details.get(SYSTEM_DATA_LOGIN_USER, {})
            current_user = users.get(self.config_data.username, {})
            system_data.user_level = current_user.get(SYSTEM_DATA_LOGIN_USER_LEVEL)

            self._system = system_data

            message = (
                f"User {self.config_data.username} level is {self._system.user_level}, "
                f"Interface status switch will not be created as it requires admin role"
            )

            self.unique_log(logging.INFO, message)

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(f"Failed to extract System data, Error: {ex}, Line: {line_number}")

    def _extract_interfaces(self, data: dict):
        try:
            interface_types = data.get(API_DATA_INTERFACES, {})

            for interface_type in interface_types:
                interfaces = interface_types.get(interface_type)

                for interface_name in interfaces:
                    interface_data = interfaces.get(interface_name, {})
                    self._extract_interface(interface_name, interface_data, interface_type)

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(f"Failed to extract Interfaces data, Error: {ex}, Line: {line_number}")

    def _extract_interface(self, name: str, data: dict, interface_type: str | None = None) -> EdgeOSInterfaceData:
        interface = self._interfaces.get(name)

        try:
            if data is not None:
                if interface is None:
                    interface = EdgeOSInterfaceData(name)
                    interface.set_type(interface_type)

                    if interface.handler == InterfaceHandlers.IGNORED:
                        message = f"Interface {name} is ignored, no entities will be created, Data: {data}"
                        self.unique_log(logging.INFO, message)

                interface.description = data.get(INTERFACE_DATA_DESCRIPTION)
                interface.duplex = data.get(INTERFACE_DATA_DUPLEX)
                interface.speed = data.get(INTERFACE_DATA_SPEED)
                interface.bridge_group = data.get(INTERFACE_DATA_BRIDGE_GROUP)
                interface.address = data.get(INTERFACE_DATA_ADDRESS)
                interface.aging = data.get(INTERFACE_DATA_AGING)
                interface.bridged_conntrack = data.get(INTERFACE_DATA_BRIDGED_CONNTRACK)
                interface.hello_time = data.get(INTERFACE_DATA_HELLO_TIME)
                interface.max_age = data.get(INTERFACE_DATA_MAX_AGE)
                interface.priority = data.get(INTERFACE_DATA_PRIORITY)
                interface.promiscuous = data.get(INTERFACE_DATA_PROMISCUOUS)
                interface.stp = data.get(INTERFACE_DATA_STP, FALSE_STR).lower() == TRUE_STR

                self._interfaces[interface.unique_id] = interface

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(
                f"Failed to extract interface data for {name}/{interface_type}, "
                f"Error: {ex}, "
                f"Line: {line_number}"
            )

        return interface

    @staticmethod
    def _update_interface_stats(interface: EdgeOSInterfaceData, data: dict):
        try:
            if data is not None:
                interface.up = str(data.get(INTERFACE_DATA_UP, False)).lower() == TRUE_STR
                interface.l1up = str(data.get(INTERFACE_DATA_LINK_UP, False)).lower() == TRUE_STR
                interface.mac = data.get(INTERFACE_DATA_MAC)
                interface.multicast = data.get(INTERFACE_DATA_MULTICAST, 0)
                interface.address = data.get(ADDRESS_LIST, [])

                directions = [interface.received, interface.sent]

                for direction in directions:
                    stat_data = {}
                    for stat_key in TRAFFIC_DATA_INTERFACE_ITEMS:
                        key = f"{direction.direction}_{stat_key}"
                        stat_data_item = TRAFFIC_DATA_INTERFACE_ITEMS.get(stat_key)

                        stat_data[stat_data_item] = float(data.get(key))

                    direction.update(stat_data)

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(
                f"Failed to update interface statistics for {interface.name}, "
                f"Error: {ex}, "
                f"Line: {line_number}"
            )

    @staticmethod
    def _update_device_stats(device_data: EdgeOSDeviceData, data: dict):
        try:
            if not device_data.is_leased:
                stats = [device_data.received, device_data.sent]

                for stat in stats:
                    stat_data = {}
                    for stat_key in TRAFFIC_DATA_DEVICE_ITEMS:
                        key = f"{stat.direction}_{stat_key}"
                        stat_data_item = TRAFFIC_DATA_DEVICE_ITEMS.get(stat_key)

                        stat_data[stat_data_item] = data.get(key)

                    stat.update(stat_data)

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(
                f"Failed to update device statistics for {device_data.hostname}, "
                f"Error: {ex}, "
                f"Line: {line_number}"
            )

    def _update_system_stats(self, system_stats_data: dict, discovery_data: dict):
        try:
            system_data = self._system

            system_data.fw_version = discovery_data.get(DISCOVER_DATA_FW_VERSION)
            system_data.product = discovery_data.get(DISCOVER_DATA_PRODUCT)

            uptime = float(system_stats_data.get(SYSTEM_STATS_DATA_UPTIME, 0))

            system_data.cpu = int(system_stats_data.get(SYSTEM_STATS_DATA_CPU, 0))
            system_data.mem = int(system_stats_data.get(SYSTEM_STATS_DATA_MEM, 0))

            if uptime != system_data.uptime:
                system_data.uptime = uptime
                system_data.last_reset = self._get_last_reset(uptime)

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(
                f"Failed to update system statistics, "
                f"Error: {ex}, "
                f"Line: {line_number}"
            )

    def _extract_unknown_devices(self):
        try:
            unknown_devices = 0
            data_leases_stats = self.api.data.get(API_DATA_DHCP_STATS, {})

            subnets = data_leases_stats.get(DHCP_SERVER_STATS, {})

            for subnet in subnets:
                subnet_data = subnets.get(subnet, {})
                unknown_devices += int(subnet_data.get(DHCP_SERVER_LEASED, 0))

            self._system.leased_devices = unknown_devices

            data_leases = self.api.data.get(API_DATA_DHCP_LEASES, {})
            data_server_leases = data_leases.get(DHCP_SERVER_LEASES, {})

            for subnet in data_server_leases:
                subnet_data = data_server_leases.get(subnet, {})

                for ip in subnet_data:
                    device_data = subnet_data.get(ip)

                    hostname = device_data.get(DHCP_SERVER_LEASES_CLIENT_HOSTNAME)

                    static_mapping_data = {
                        DHCP_SERVER_IP_ADDRESS: ip,
                        DHCP_SERVER_MAC_ADDRESS: device_data.get(DEVICE_DATA_MAC)
                    }

                    self._set_device(hostname, None, static_mapping_data, True)
        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(f"Failed to extract Unknown Devices data, Error: {ex}, Line: {line_number}")

    def _extract_devices(self, data: dict):
        try:
            service = data.get(DATA_SYSTEM_SERVICE, {})
            dhcp_server = service.get(DATA_SYSTEM_SERVICE_DHCP_SERVER, {})
            shared_network_names = dhcp_server.get(DHCP_SERVER_SHARED_NETWORK_NAME, {})

            for shared_network_name in shared_network_names:
                shared_network_name_data = shared_network_names.get(shared_network_name, {})
                subnets = shared_network_name_data.get(DHCP_SERVER_SUBNET, {})

                for subnet in subnets:
                    subnet_data = subnets.get(subnet, {})

                    domain_name = subnet_data.get(SYSTEM_DATA_DOMAIN_NAME)
                    static_mappings = subnet_data.get(DHCP_SERVER_STATIC_MAPPING, {})

                    for hostname in static_mappings:
                        static_mapping_data = static_mappings.get(hostname, {})

                        self._set_device(hostname, domain_name, static_mapping_data, False)
        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(f"Failed to extract Devices data, Error: {ex}, Line: {line_number}")

    def _set_device(self, hostname: str, domain_name: str | None, static_mapping_data: dict, is_leased: bool):
        ip_address = static_mapping_data.get(DHCP_SERVER_IP_ADDRESS)
        mac_address = static_mapping_data.get(DHCP_SERVER_MAC_ADDRESS)

        existing_device_data = self._devices.get(mac_address)

        if existing_device_data is None:
            device_data = EdgeOSDeviceData(hostname, ip_address, mac_address, domain_name, is_leased)

        else:
            device_data = existing_device_data

        self._devices[device_data.unique_id] = device_data
        self._devices_ip_mapping[device_data.ip] = device_data.unique_id

    def _get_device(self, unique_id: str) -> EdgeOSDeviceData | None:
        device = self._devices.get(unique_id)

        return device

    def _get_device_by_ip(self, ip: str) -> EdgeOSDeviceData | None:
        unique_id = self._devices_ip_mapping.get(ip)

        device = self._get_device(unique_id)

        return device

    def _set_ha_device(self, name: str, model: str, manufacturer: str, version: str | None = None):
        device_details = self.device_manager.get(name)

        device_details_data = {
            "identifiers": {(DEFAULT_NAME, name)},
            "name": name,
            "manufacturer": manufacturer,
            "model": model
        }

        if version is not None:
            device_details_data["sw_version"] = version

        if device_details is None or device_details != device_details_data:
            self.device_manager.set(name, device_details_data)

            _LOGGER.debug(f"Created HA device {name} [{model}]")

    def _load_main_device(self):
        self._set_ha_device(self.system_name, self._system.product, MANUFACTURER, self._system.fw_version)

    def _load_device_device(self, device: EdgeOSDeviceData):
        name = self._get_device_name(device)
        self._set_ha_device(name, "Device", DEFAULT_NAME)

    def _load_interface_device(self, interface: EdgeOSInterfaceData):
        name = self._get_interface_name(interface)
        self._set_ha_device(name, "Interface", DEFAULT_NAME)

    def _load_unit_select(self):
        try:
            device_name = self.system_name
            entity_name = f"{device_name} Data Unit"

            attributes = {
                ATTR_FRIENDLY_NAME: entity_name,
            }

            unique_id = EntityData.generate_unique_id(DOMAIN_SELECT, entity_name)
            state = self.storage_api.unit

            entity_description = SelectEntityDescription(
                key=unique_id,
                name=entity_name,
                device_class=f"{DOMAIN}__{STORAGE_DATA_UNIT}",
                options=list(UNIT_OF_MEASUREMENT_MAPPING.keys()),
                entity_category=EntityCategory.CONFIG
            )

            self.set_action(unique_id, ACTION_CORE_ENTITY_SELECT_OPTION, self._set_unit)

            self.entity_manager.set_entity(DOMAIN_SELECT,
                                           self.entry_id,
                                           state,
                                           attributes,
                                           device_name,
                                           entity_description)

        except Exception as ex:
            self.log_exception(ex, f"Failed to load select for Data Unit")

    def _load_unknown_devices_sensor(self):
        device_name = self.system_name
        entity_name = f"{device_name} Unknown Devices"

        try:
            state = self._system.leased_devices

            leased_devices = []

            for unique_id in self._devices:
                device = self._devices.get(unique_id)

                if device.is_leased:
                    leased_devices.append(f"{device.hostname} ({device.ip})")

            attributes = {
                ATTR_FRIENDLY_NAME: entity_name,
                DHCP_SERVER_LEASED: leased_devices
            }

            unique_id = EntityData.generate_unique_id(DOMAIN_SENSOR, entity_name)
            icon = "mdi:help-network-outline"

            entity_description = SensorEntityDescription(
                key=unique_id,
                name=entity_name,
                icon=icon,
                state_class=SensorStateClass.MEASUREMENT
            )

            self.entity_manager.set_entity(DOMAIN_SENSOR,
                                           self.entry_id,
                                           state,
                                           attributes,
                                           device_name,
                                           entity_description)

        except Exception as ex:
            self.log_exception(
                ex, f"Failed to load sensor for {entity_name}"
            )

    def _load_cpu_sensor(self):
        device_name = self.system_name
        entity_name = f"{device_name} CPU Usage"

        try:
            state = self._system.cpu

            attributes = {
                ATTR_FRIENDLY_NAME: entity_name,
            }

            unique_id = EntityData.generate_unique_id(DOMAIN_SENSOR, entity_name)
            icon = "mdi:chip"

            entity_description = SensorEntityDescription(
                key=unique_id,
                name=entity_name,
                icon=icon,
                state_class=SensorStateClass.MEASUREMENT,
                native_unit_of_measurement="%",
            )

            self.entity_manager.set_entity(DOMAIN_SENSOR,
                                           self.entry_id,
                                           state,
                                           attributes,
                                           device_name,
                                           entity_description)

        except Exception as ex:
            self.log_exception(
                ex, f"Failed to load sensor for {entity_name}"
            )

    def _load_ram_sensor(self):
        device_name = self.system_name
        entity_name = f"{device_name} RAM Usage"

        try:
            state = self._system.mem

            attributes = {
                ATTR_FRIENDLY_NAME: entity_name
            }

            unique_id = EntityData.generate_unique_id(DOMAIN_SENSOR, entity_name)
            icon = "mdi:memory"

            entity_description = SensorEntityDescription(
                key=unique_id,
                name=entity_name,
                icon=icon,
                state_class=SensorStateClass.MEASUREMENT,
                native_unit_of_measurement="%",
            )

            self.entity_manager.set_entity(DOMAIN_SENSOR,
                                           self.entry_id,
                                           state,
                                           attributes,
                                           device_name,
                                           entity_description)

        except Exception as ex:
            self.log_exception(
                ex, f"Failed to load sensor for {entity_name}"
            )

    def _load_uptime_sensor(self):
        device_name = self.system_name
        entity_name = f"{device_name} Last Restart"

        try:
            state = self._system.last_reset

            attributes = {
                ATTR_FRIENDLY_NAME: entity_name
            }

            unique_id = EntityData.generate_unique_id(DOMAIN_SENSOR, entity_name)
            icon = "mdi:credit-card-clock"

            entity_description = SensorEntityDescription(
                key=unique_id,
                name=entity_name,
                icon=icon,
                state_class=SensorStateClass.TOTAL_INCREASING
            )

            self.entity_manager.set_entity(DOMAIN_SENSOR,
                                           self.entry_id,
                                           state,
                                           attributes,
                                           device_name,
                                           entity_description)

        except Exception as ex:
            self.log_exception(
                ex, f"Failed to load sensor for {entity_name}"
            )

    def _load_firmware_upgrade_binary_sensor(self):
        device_name = self.system_name
        entity_name = f"{device_name} Firmware Upgrade"

        try:
            state = STATE_ON if self._system.upgrade_available else STATE_OFF

            attributes = {
                ATTR_FRIENDLY_NAME: entity_name,
                SYSTEM_INFO_DATA_FW_LATEST_URL: self._system.upgrade_url,
                SYSTEM_INFO_DATA_FW_LATEST_VERSION: self._system.upgrade_version
            }

            unique_id = EntityData.generate_unique_id(DOMAIN_BINARY_SENSOR, entity_name)

            entity_description = BinarySensorEntityDescription(
                key=unique_id,
                name=entity_name,
                device_class=BinarySensorDeviceClass.UPDATE
            )

            self.entity_manager.set_entity(DOMAIN_BINARY_SENSOR,
                                           self.entry_id,
                                           state,
                                           attributes,
                                           device_name,
                                           entity_description)

        except Exception as ex:
            self.log_exception(
                ex, f"Failed to load sensor for {entity_name}"
            )

    def _load_log_incoming_messages_switch(self):
        device_name = self.system_name
        entity_name = f"{device_name} Log Incoming Messages"

        try:
            state = self.storage_api.log_incoming_messages

            attributes = {
                ATTR_FRIENDLY_NAME: entity_name
            }

            unique_id = EntityData.generate_unique_id(DOMAIN_SWITCH, entity_name)

            icon = "mdi:math-log"

            entity_description = SwitchEntityDescription(
                key=unique_id,
                name=entity_name,
                icon=icon,
                entity_category=EntityCategory.CONFIG
            )

            self.entity_manager.set_entity(DOMAIN_SWITCH,
                                           self.entry_id,
                                           state,
                                           attributes,
                                           device_name,
                                           entity_description)

            self.set_action(unique_id, ACTION_CORE_ENTITY_TURN_ON, self._enable_log_incoming_messages)
            self.set_action(unique_id, ACTION_CORE_ENTITY_TURN_OFF, self._disable_log_incoming_messages)

        except Exception as ex:
            self.log_exception(
                ex, f"Failed to load log incoming messages switch for {entity_name}"
            )

    def _load_device_tracker(self, device: EdgeOSDeviceData):
        device_name = self._get_device_name(device)
        entity_name = f"{device_name}"

        try:
            state = device.last_activity_in_seconds <= self.storage_api.consider_away_interval

            attributes = {
                ATTR_FRIENDLY_NAME: entity_name,
                LAST_ACTIVITY: device.last_activity_in_seconds
            }

            unique_id = EntityData.generate_unique_id(DOMAIN_DEVICE_TRACKER, entity_name)

            entity_description = EntityDescription(
                key=unique_id,
                name=entity_name
            )

            details = {
                ENTITY_UNIQUE_ID: device.unique_id
            }

            is_monitored = self.storage_api.monitored_devices.get(device.unique_id, False)

            self.entity_manager.set_entity(DOMAIN_DEVICE_TRACKER,
                                           self.entry_id,
                                           state,
                                           attributes,
                                           device_name,
                                           entity_description,
                                           destructors=[not is_monitored],
                                           details=details)

        except Exception as ex:
            self.log_exception(
                ex, f"Failed to load device tracker for {entity_name}"
            )

    def _load_device_monitor_switch(self, device: EdgeOSDeviceData):
        device_name = self._get_device_name(device)
        entity_name = f"{device_name} Monitored"

        try:
            state = self.storage_api.monitored_devices.get(device.unique_id, False)

            attributes = {
                ATTR_FRIENDLY_NAME: entity_name
            }

            unique_id = EntityData.generate_unique_id(DOMAIN_SWITCH, entity_name)
            icon = "mdi:monitor-eye"

            entity_description = SwitchEntityDescription(
                key=unique_id,
                name=entity_name,
                icon=icon,
                entity_category=EntityCategory.CONFIG
            )

            details = {
                ENTITY_UNIQUE_ID: device.unique_id
            }

            self.set_action(unique_id, ACTION_CORE_ENTITY_TURN_ON, self._set_device_monitored)
            self.set_action(unique_id, ACTION_CORE_ENTITY_TURN_OFF, self._set_device_unmonitored)

            self.entity_manager.set_entity(DOMAIN_SWITCH,
                                           self.entry_id,
                                           state,
                                           attributes,
                                           device_name,
                                           entity_description,
                                           details=details)

        except Exception as ex:
            self.log_exception(
                ex, f"Failed to load switch for {entity_name}"
            )

    def _load_device_stats_sensor(self,
                                  device: EdgeOSDeviceData,
                                  entity_suffix: str,
                                  state: str | int | float | None):

        device_name = self._get_device_name(device)
        entity_name = f"{device_name} {entity_suffix}"

        is_monitored = self.storage_api.monitored_devices.get(device.unique_id, False)
        icon = STATS_ICONS.get(entity_suffix)

        is_rate_stats = entity_suffix in STATS_RATE

        if is_rate_stats:
            unit_of_measurement = self._get_rate_unit_of_measurement()
            state = self._convert_unit(state)

        elif entity_suffix in STATS_TRAFFIC:
            unit_of_measurement = self._get_unit_of_measurement()
            state = self._convert_unit(state)

        else:
            unit_of_measurement = str(STATS_UNITS.get(entity_suffix)).capitalize()

        state_class = SensorStateClass.MEASUREMENT if is_rate_stats else SensorStateClass.TOTAL_INCREASING

        self._load_stats_sensor(device_name, entity_name, state, unit_of_measurement, icon, state_class, is_monitored)

    def _load_interface_stats_sensor(self,
                                     interface: EdgeOSInterfaceData,
                                     entity_suffix: str,
                                     state: str | int | float | None):

        device_name = self._get_interface_name(interface)
        entity_name = f"{device_name} {entity_suffix}"

        is_monitored = self.storage_api.monitored_interfaces.get(interface.unique_id, False)

        is_rate_stats = entity_suffix in STATS_RATE
        icon = STATS_ICONS.get(entity_suffix)

        if is_rate_stats:
            unit_of_measurement = self._get_rate_unit_of_measurement()
            state = self._convert_unit(state)

        elif entity_suffix in STATS_TRAFFIC:
            unit_of_measurement = self._get_unit_of_measurement()
            state = self._convert_unit(state)

        else:
            unit_of_measurement = str(STATS_UNITS.get(entity_suffix)).capitalize()

        state_class = SensorStateClass.MEASUREMENT if is_rate_stats else SensorStateClass.TOTAL_INCREASING

        self._load_stats_sensor(device_name, entity_name, state, unit_of_measurement, icon, state_class, is_monitored)

    def _load_stats_sensor(self,
                           device_name: str,
                           entity_name: str,
                           state: str | int | float | None,
                           unit_of_measurement: str,
                           icon: str | None,
                           state_class: SensorStateClass,
                           is_monitored: bool):
        try:
            attributes = {
                ATTR_FRIENDLY_NAME: entity_name
            }

            unique_id = EntityData.generate_unique_id(DOMAIN_SENSOR, entity_name)

            entity_description = SensorEntityDescription(
                key=unique_id,
                name=entity_name,
                icon=icon,
                state_class=state_class,
                native_unit_of_measurement=unit_of_measurement,
            )

            if unit_of_measurement.lower() in [TRAFFIC_DATA_ERRORS, TRAFFIC_DATA_PACKETS, TRAFFIC_DATA_DROPPED]:
                state = self._format_number(state)

            self.entity_manager.set_entity(DOMAIN_SENSOR,
                                           self.entry_id,
                                           state,
                                           attributes,
                                           device_name,
                                           entity_description,
                                           destructors=[not is_monitored])

        except Exception as ex:
            self.log_exception(
                ex, f"Failed to load sensor for {entity_name}"
            )

    def _load_interface_status_switch(self, interface: EdgeOSInterfaceData):
        interface_name = self._get_interface_name(interface)
        entity_name = f"{interface_name} Status"

        try:
            state = interface.up

            attributes = {
                ATTR_FRIENDLY_NAME: entity_name,
                ADDRESS_LIST: interface.address
            }

            unique_id = EntityData.generate_unique_id(DOMAIN_SWITCH, entity_name)
            icon = "mdi:eye-settings"

            entity_description = SwitchEntityDescription(
                key=unique_id,
                name=entity_name,
                icon=icon,
                entity_category=EntityCategory.CONFIG
            )

            details = {
                ENTITY_UNIQUE_ID: interface.unique_id
            }

            self.set_action(unique_id, ACTION_CORE_ENTITY_TURN_ON, self._set_interface_enabled)
            self.set_action(unique_id, ACTION_CORE_ENTITY_TURN_OFF, self._set_interface_disabled)

            self.entity_manager.set_entity(DOMAIN_SWITCH,
                                           self.entry_id,
                                           state,
                                           attributes,
                                           interface_name,
                                           entity_description,
                                           details=details)

        except Exception as ex:
            self.log_exception(
                ex, f"Failed to load switch for {entity_name}"
            )

    def _load_interface_status_binary_sensor(self, interface: EdgeOSInterfaceData):
        interface_name = self._get_interface_name(interface)
        entity_name = f"{interface_name} Status"

        try:
            state = STATE_ON if interface.up else STATE_OFF

            attributes = {
                ATTR_FRIENDLY_NAME: entity_name,
                ADDRESS_LIST: interface.address
            }

            unique_id = EntityData.generate_unique_id(DOMAIN_BINARY_SENSOR, entity_name)

            entity_description = BinarySensorEntityDescription(
                key=unique_id,
                name=entity_name,
                device_class=BinarySensorDeviceClass.CONNECTIVITY
            )

            self.entity_manager.set_entity(DOMAIN_BINARY_SENSOR,
                                           self.entry_id,
                                           state,
                                           attributes,
                                           interface_name,
                                           entity_description)

        except Exception as ex:
            self.log_exception(
                ex, f"Failed to load binary sensor for {entity_name}"
            )

    def _load_interface_connected_binary_sensor(self, interface: EdgeOSInterfaceData):
        interface_name = self._get_interface_name(interface)
        entity_name = f"{interface_name} Connected"

        try:
            state = STATE_ON if interface.l1up else STATE_OFF

            attributes = {
                ATTR_FRIENDLY_NAME: entity_name,
                ADDRESS_LIST: interface.address
            }

            unique_id = EntityData.generate_unique_id(DOMAIN_BINARY_SENSOR, entity_name)

            entity_description = BinarySensorEntityDescription(
                key=unique_id,
                name=entity_name,
                device_class=BinarySensorDeviceClass.CONNECTIVITY
            )

            self.entity_manager.set_entity(DOMAIN_BINARY_SENSOR,
                                           self.entry_id,
                                           state,
                                           attributes,
                                           interface_name,
                                           entity_description)

        except Exception as ex:
            self.log_exception(
                ex, f"Failed to load binary sensor for {entity_name}"
            )

    def _load_interface_monitor_switch(self, interface: EdgeOSInterfaceData):
        interface_name = self._get_interface_name(interface)
        entity_name = f"{interface_name} Monitored"

        try:
            state = self.storage_api.monitored_interfaces.get(interface.unique_id, False)

            attributes = {
                ATTR_FRIENDLY_NAME: entity_name
            }

            unique_id = EntityData.generate_unique_id(DOMAIN_SWITCH, entity_name)
            icon = None

            entity_description = SwitchEntityDescription(
                key=unique_id,
                name=entity_name,
                icon=icon,
                entity_category=EntityCategory.CONFIG
            )

            details = {
                ENTITY_UNIQUE_ID: interface.unique_id
            }

            self.set_action(unique_id, ACTION_CORE_ENTITY_TURN_ON, self._set_interface_monitored)
            self.set_action(unique_id, ACTION_CORE_ENTITY_TURN_OFF, self._set_interface_unmonitored)

            self.entity_manager.set_entity(DOMAIN_SWITCH,
                                           self.entry_id,
                                           state,
                                           attributes,
                                           interface_name,
                                           entity_description,
                                           details=details)

        except Exception as ex:
            self.log_exception(
                ex, f"Failed to load switch for {entity_name}"
            )

    async def _set_interface_enabled(self, entity: EntityData):
        interface_item = self._get_interface_from_entity(entity)

        await self.api.set_interface_state(interface_item, True)

    async def _set_interface_disabled(self, entity: EntityData):
        interface_item = self._get_interface_from_entity(entity)

        await self.api.set_interface_state(interface_item, False)

    async def _set_interface_monitored(self, entity: EntityData):
        interface_item = self._get_interface_from_entity(entity)

        await self.storage_api.set_monitored_interface(interface_item.unique_id, True)

    async def _set_interface_unmonitored(self, entity: EntityData):
        interface_item = self._get_interface_from_entity(entity)

        await self.storage_api.set_monitored_interface(interface_item.unique_id, False)

    async def _set_device_monitored(self, entity: EntityData):
        device_item = self._get_device_from_entity(entity)

        await self.storage_api.set_monitored_device(device_item.unique_id, True)

    async def _set_device_unmonitored(self, entity: EntityData):
        device_item = self._get_device_from_entity(entity)

        await self.storage_api.set_monitored_device(device_item.unique_id, False)

    async def _enable_log_incoming_messages(self, entity: EntityData):
        await self.storage_api.set_log_incoming_messages(True)

    async def _disable_log_incoming_messages(self, entity: EntityData):
        await self.storage_api.set_log_incoming_messages(False)

    async def _set_unit(self, entity: EntityData, option: str):
        await self.storage_api.set_unit(option)

        await self._reload_integration()

    def _get_device_from_entity(self, entity: EntityData) -> EdgeOSDeviceData:
        unique_id = entity.details.get(ENTITY_UNIQUE_ID)
        device_item = self._get_device(unique_id)

        return device_item

    def _get_interface_from_entity(self, entity: EntityData) -> EdgeOSInterfaceData:
        unique_id = entity.details.get(ENTITY_UNIQUE_ID)
        interface_item = self._interfaces.get(unique_id)

        return interface_item

    def _convert_unit(self, value: float) -> float:
        unit_factor = UNIT_MAPPING.get(self.storage_api.unit, BYTE)
        result = value

        if result > 0:
            result = result / unit_factor

        digits = 0 if unit_factor == BYTE else 3

        result = self._format_number(result, digits)

        return result

    @staticmethod
    def _format_number(value: int | float | None, digits: int = 0) -> int | float:
        if value is None:
            value = 0

        value_str = f"{value:.{digits}f}"
        result = int(value_str) if digits == 0 else float(value_str)

        return result

    def _get_unit_of_measurement(self) -> str:
        result = UNIT_OF_MEASUREMENT_MAPPING.get(self.storage_api.unit, "B")

        return result

    def _get_rate_unit_of_measurement(self) -> str:
        unit_of_measurement = self._get_unit_of_measurement()
        result = f"{unit_of_measurement}/ps"

        return result

    async def _reload_integration(self):
        data = {
            ENTITY_CONFIG_ENTRY_ID: self.entry_id
        }

        await self._hass.services.async_call(HA_NAME, SERVICE_RELOAD, data)

    def _update_configuration(self, service_call):
        self._hass.async_create_task(self._async_update_configuration(service_call))

    async def _async_update_configuration(self, service_call):
        service_data = service_call.data
        device_id = service_data.get(CONF_DEVICE_ID)

        _LOGGER.info(f"Update configuration called with data: {service_data}")

        if device_id is None:
            _LOGGER.error("Operation cannot be performed, missing device information")

        else:
            dr = async_get_device_registry(self._hass)
            device = dr.devices.get(device_id)
            can_handle_device = self.entry_id in device.config_entries

            if can_handle_device:
                updated = await self._update_configuration_data(service_data)

                if updated:
                    await self._reload_integration()

    async def _update_configuration_data(self, data: dict):
        result = False

        storage_data_import_keys: dict[str, Callable[[int | bool | str], Awaitable[None]]] = {
            STORAGE_DATA_CONSIDER_AWAY_INTERVAL: self.storage_api.set_consider_away_interval,
            STORAGE_DATA_UPDATE_ENTITIES_INTERVAL: self.storage_api.set_update_entities_interval,
            STORAGE_DATA_UPDATE_API_INTERVAL: self.storage_api.set_update_api_interval,
            STORAGE_DATA_LOG_INCOMING_MESSAGES: self.storage_api.set_log_incoming_messages,
            STORAGE_DATA_UNIT: self.storage_api.set_unit
        }

        for key in storage_data_import_keys:
            data_item = data.get(key.replace(STRING_DASH, STRING_UNDERSCORE))
            existing_data = self.storage_api.data.get(key)

            if data_item is not None and data_item != existing_data:
                if not result:
                    result = True

                set_func = storage_data_import_keys.get(key)

                await set_func(data_item)

        return result

    @staticmethod
    def _get_last_reset(uptime):
        now = datetime.now().timestamp()
        last_reset = int(now) - uptime

        result = datetime.fromtimestamp(last_reset)

        return result

    def unique_log(self, log_level: int, message: str):
        if message not in self._unique_messages:
            self._unique_messages.append(message)

            _LOGGER.log(log_level, self._unique_messages)
