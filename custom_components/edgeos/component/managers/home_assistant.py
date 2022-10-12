"""
Support for Shinobi Video.
For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/shinobi/
"""
from __future__ import annotations

import asyncio
import datetime
import logging
import sys

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntityDescription,
)
from homeassistant.components.sensor import SensorEntityDescription
from homeassistant.components.switch import SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import async_get as async_get_device_registry
from homeassistant.helpers.entity import EntityCategory, EntityDescription

from ...configuration.managers.configuration_manager import ConfigurationManager
from ...configuration.models.config_data import ConfigData
from ...core.helpers.enums import ConnectivityStatus
from ...core.managers.home_assistant import HomeAssistantManager
from ...core.models.entity_data import EntityData
from ...core.models.select_description import SelectDescription
from ..api.api import IntegrationAPI
from ..api.storage_api import StorageAPI
from ..api.websocket import IntegrationWS
from ..helpers.const import *
from ..models.edge_os_device_data import EdgeOSDeviceData
from ..models.edge_os_interface_data import EdgeOSInterfaceData
from ..models.edge_os_system_data import EdgeOSSystemData

_LOGGER = logging.getLogger(__name__)


class ShinobiHomeAssistantManager(HomeAssistantManager):
    def __init__(self, hass: HomeAssistant):
        super().__init__(hass, SCAN_INTERVAL, HEARTBEAT_INTERVAL_SECONDS)

        self._storage_api: StorageAPI = StorageAPI(self._hass)
        self._api: IntegrationAPI = IntegrationAPI(self._hass, self._api_data_changed, self._api_status_changed)
        self._ws: IntegrationWS = IntegrationWS(self._hass, self._ws_data_changed, self._ws_status_changed)
        self._config_manager: ConfigurationManager | None = None
        self._system: EdgeOSSystemData | None = None
        self._devices: dict[str, EdgeOSDeviceData] = {}
        self._devices_ip_mapping: dict[str, str] = {}
        self._interfaces: dict[str, EdgeOSInterfaceData] = {}
        self._unknown_devices: int | None = None

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

            self.update()

    async def _ws_data_changed(self):
        if self.api.status == ConnectivityStatus.Connected:
            await self._extract_ws_data()

            self.update()

    async def _api_status_changed(self, status: ConnectivityStatus):
        _LOGGER.info(f"API Status changed to {status}, WS Status: {self.ws.status}")
        if status == ConnectivityStatus.Connected:
            if self.ws.status == ConnectivityStatus.NotConnected:
                log_incoming_messages = self.storage_api.log_incoming_messages
                await self.ws.update_api_data(self.api.data, log_incoming_messages)

                await self.ws.initialize(self.config_data)

        if status == ConnectivityStatus.Disconnected:
            if self.ws.status == ConnectivityStatus.Connected:
                await self.ws.terminate()

    async def _ws_status_changed(self, status: ConnectivityStatus):
        _LOGGER.info(f"WS Status changed to {status}, API Status: {self.api.status}")

        if status == ConnectivityStatus.NotConnected:
            if self.api.status == ConnectivityStatus.Connected:
                await self.ws.initialize(self.config_data)

                if not self.ws.status == ConnectivityStatus.NotConnected:
                    await asyncio.sleep(WS_RECONNECT_INTERVAL.total_seconds())

        if status == ConnectivityStatus.Connected:
            await self.async_update(datetime.now())

    async def async_component_initialize(self, entry: ConfigEntry):
        try:
            self._config_manager = ConfigurationManager(self._hass, self.api)
            await self._config_manager.load(entry)

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(f"Failed to async_component_initialize, error: {ex}, line: {line_number}")

    async def async_initialize_data_providers(self):
        await self.storage_api.initialize(self.config_data)

        has_legacy_configuration = False

        if self._entry is not None:
            if self._entry.data is not None:
                unit = self._entry.data.get(CONF_UNIT)

                if unit is not None:
                    await self.storage_api.set_unit(unit)

                    has_legacy_configuration = True

            if self._entry.options is not None:
                consider_away_interval = self._entry.options.get(CONF_LOG_INCOMING_MESSAGES)
                log_incoming_messages = self._entry.options.get(CONF_CONSIDER_AWAY_INTERVAL)

                has_legacy_configuration = consider_away_interval is not None or log_incoming_messages is not None

                if consider_away_interval is not None:
                    await self.storage_api.set_consider_away_interval(consider_away_interval)

                if log_incoming_messages is not None:
                    await self.storage_api.set_log_incoming_messages(log_incoming_messages)

        if has_legacy_configuration:
            _LOGGER.info("Starting configuration migration")

            data = {}
            for key in self._entry.data.keys():
                if key != CONF_UNIT:
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
        await self.ws.terminate()

    async def async_update_data_providers(self):
        try:
            await self.api.async_update()

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(f"Failed to async_update_data_providers, Error: {ex}, Line: {line_number}")

    def register_services(self, entry: ConfigEntry | None = None):
        self._hass.services.async_register(DOMAIN, SERVICE_UPDATE_CONFIGURATION, self._update_configuration)

    def load_devices(self):
        if self._system.product is None:
            return

        self._load_main_device()

        for unique_id in self._devices:
            device_item = self._get_device(unique_id)
            self._load_device_device(device_item)

        for unique_id in self._interfaces:
            interface_item = self._interfaces.get(unique_id)
            self._load_interface_device(interface_item)

    def load_entities(self):
        if self._system.product is None:
            return

        self._load_unit_select()
        self._load_unknown_devices_sensor()
        self._load_cpu_sensor()
        self._load_ram_sensor()
        self._load_uptime_sensor()
        self._load_firmware_upgrade_binary_sensor()
        self._load_log_incoming_messages_switch()
        self._load_store_debug_data_switch()

        for unique_id in self._devices:
            device_item = self._get_device(unique_id)

            if not device_item.is_leased:
                self._load_device_monitor_switch(device_item)

                self._load_device_received_rate_sensor(device_item)
                self._load_device_received_traffic_sensor(device_item)
                self._load_device_sent_rate_sensor(device_item)
                self._load_device_sent_traffic_sensor(device_item)

                self._load_device_tracker(device_item)

        for unique_id in self._interfaces:
            interface_item = self._interfaces.get(unique_id)
            self._load_interface_monitor_switch(interface_item)
            self._load_interface_status_switch(interface_item)

            self._load_interface_received_rate_sensor(interface_item)
            self._load_interface_received_traffic_sensor(interface_item)
            self._load_interface_received_dropped_sensor(interface_item)
            self._load_interface_received_errors_sensor(interface_item)
            self._load_interface_received_packets_sensor(interface_item)

            self._load_interface_sent_rate_sensor(interface_item)
            self._load_interface_sent_traffic_sensor(interface_item)
            self._load_interface_sent_dropped_sensor(interface_item)
            self._load_interface_sent_errors_sensor(interface_item)
            self._load_interface_sent_packets_sensor(interface_item)

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

                if interface_item is not None:
                    self._update_interface_stats(interface_item, stats)
        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(f"Failed to extract WS data, Error: {ex}, Line: {line_number}")

    async def _extract_api_data(self):
        try:
            await self.storage_api.debug_log_api(self.api.data)

            data = self.api.data.get(API_DATA_SYSTEM, {})
            system_info = self.api.data.get(SYS_INFO_KEY, {})

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

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(f"Failed to extract API data, Error: {ex}, Line: {line_number}")

    def _extract_system(self, data: dict, system_info: dict):
        try:
            system_details = data.get(API_DATA_SYSTEM, {})

            system_data = EdgeOSSystemData()

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

            self._system = system_data
        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(f"Failed to extract System data, Error: {ex}, Line: {line_number}")

    def _extract_interfaces(self, data: dict):
        try:
            interface_types = data.get(API_DATA_INTERFACES, {})

            for interface_type_name in interface_types:
                if interface_type_name in MONITORED_INTERFACE_TYPES:
                    interface_type_data = interface_types.get(interface_type_name)

                    for interface_name in interface_type_data:
                        interface_data = interface_type_data.get(interface_name, {})
                        self._extract_interface(interface_name, interface_type_name, interface_data)
        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(f"Failed to extract Interfaces data, Error: {ex}, Line: {line_number}")

    def _extract_interface(self, name: str, interface_type: str, data: dict):
        try:
            interface = EdgeOSInterfaceData(name, interface_type)

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

            existing_interface_data = self._interfaces.get(interface.unique_id)

            if existing_interface_data is None or existing_interface_data != interface:
                self._interfaces[interface.unique_id] = interface

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(
                f"Failed to extract interface data for {name}/{interface_type}, "
                f"Error: {ex}, "
                f"Line: {line_number}"
            )

    @staticmethod
    def _update_interface_stats(interface_data: EdgeOSInterfaceData, data: dict):
        try:
            interface_data.up = str(data.get(INTERFACE_DATA_UP, False)).lower() == TRUE_STR
            interface_data.l1up = str(data.get(INTERFACE_DATA_LINK_UP, False)).lower() == TRUE_STR
            interface_data.mac = data.get(INTERFACE_DATA_MAC)
            interface_data.multicast = data.get(INTERFACE_DATA_MULTICAST, 0)
            interface_data.address = data.get(ADDRESS_LIST, [])

            directions = [interface_data.received, interface_data.sent]

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
                f"Failed to update interface statistics for {interface_data.name}, "
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
            data_leases_stats = self.api.data.get(DHCP_STATS_KEY, {})

            subnets = data_leases_stats.get(DHCP_SERVER_STATS, {})

            for subnet in subnets:
                subnet_data = subnets.get(subnet, {})
                unknown_devices += int(subnet_data.get(LEASED, 0))

            self._system.leased_devices = unknown_devices

            data_leases = self.api.data.get(DHCP_LEASES_KEY, {})
            data_server_leases = data_leases.get(DHCP_SERVER_LEASES, {})

            for subnet in data_server_leases:
                subnet_data = data_server_leases.get(subnet, {})

                for ip in subnet_data:
                    device_data = subnet_data.get(ip)

                    hostname = device_data.get(DHCP_SERVER_LEASES_CLIENT_HOSTNAME)

                    static_mapping_data = {
                        IP_ADDRESS: ip,
                        MAC_ADDRESS: device_data.get(DEVICE_DATA_MAC)
                    }

                    self._set_device(hostname, None, static_mapping_data, True)
        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(f"Failed to extract Unknown Devices data, Error: {ex}, Line: {line_number}")

    def _extract_devices(self, data: dict):
        try:
            service = data.get(SERVICE, {})
            dhcp_server = service.get(DHCP_SERVER, {})
            shared_network_names = dhcp_server.get(SHARED_NETWORK_NAME, {})

            for shared_network_name in shared_network_names:
                shared_network_name_data = shared_network_names.get(shared_network_name, {})
                subnets = shared_network_name_data.get(SUBNET, {})

                for subnet in subnets:
                    subnet_data = subnets.get(subnet, {})

                    domain_name = subnet_data.get(SYSTEM_DATA_DOMAIN_NAME)
                    static_mappings = subnet_data.get(STATIC_MAPPING, {})

                    for hostname in static_mappings:
                        static_mapping_data = static_mappings.get(hostname, {})

                        self._set_device(hostname, domain_name, static_mapping_data, False)
        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(f"Failed to extract Devices data, Error: {ex}, Line: {line_number}")

    def _set_device(self, hostname: str, domain_name: str | None, static_mapping_data: dict, is_leased: bool):
        ip_address = static_mapping_data.get(IP_ADDRESS)
        mac_address = static_mapping_data.get(MAC_ADDRESS)

        device_data = EdgeOSDeviceData(hostname, ip_address, mac_address, domain_name, is_leased)
        existing_device_data = self._devices.get(device_data.unique_id)

        if existing_device_data is None or existing_device_data != device_data:
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

            entity_description = SelectDescription(
                key=unique_id,
                name=entity_name,
                device_class=f"{DOMAIN}__{CONF_UNIT}",
                attr_options=tuple(UNIT_OF_MEASUREMENT_MAPPING.keys()),
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
                LEASED: leased_devices
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

            leased_devices = []

            for unique_id in self._devices:
                device = self._devices.get(unique_id)

                if device.is_leased:
                    leased_devices.append(f"{device.hostname} ({device.ip})")

            attributes = {
                ATTR_FRIENDLY_NAME: entity_name,
                LEASED: leased_devices
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

            leased_devices = []

            for unique_id in self._devices:
                device = self._devices.get(unique_id)

                if device.is_leased:
                    leased_devices.append(f"{device.hostname} ({device.ip})")

            attributes = {
                ATTR_FRIENDLY_NAME: entity_name,
                LEASED: leased_devices
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

            leased_devices = []

            for unique_id in self._devices:
                device = self._devices.get(unique_id)

                if device.is_leased:
                    leased_devices.append(f"{device.hostname} ({device.ip})")

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

    def _load_store_debug_data_switch(self):
        device_name = self.system_name
        entity_name = f"{device_name} Store Debug Data"

        try:
            state = self.storage_api.store_debug_data

            attributes = {
                ATTR_FRIENDLY_NAME: entity_name
            }

            unique_id = EntityData.generate_unique_id(DOMAIN_SWITCH, entity_name)

            icon = "mdi:file-download"

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

            self.set_action(unique_id, ACTION_CORE_ENTITY_TURN_ON, self._enable_store_debug_data)
            self.set_action(unique_id, ACTION_CORE_ENTITY_TURN_OFF, self._disable_store_debug_data)

        except Exception as ex:
            self.log_exception(
                ex, f"Failed to load store debug data switch for {entity_name}"
            )

    def _load_device_received_rate_sensor(self, device: EdgeOSDeviceData):
        unit_of_measurement = self._get_rate_unit_of_measurement()

        state = self._convert_unit(device.received.rate)

        self._load_device_stats_sensor(device,
                                       "Received Rate",
                                       state,
                                       unit_of_measurement,
                                       "mdi:upload-network-outline",
                                       SensorStateClass.MEASUREMENT)

    def _load_device_received_traffic_sensor(self, device: EdgeOSDeviceData):
        unit_of_measurement = self._get_unit_of_measurement()

        state = self._convert_unit(device.received.total)

        self._load_device_stats_sensor(device,
                                       "Received Traffic",
                                       state,
                                       unit_of_measurement,
                                       "mdi:download-network-outline")

    def _load_device_sent_rate_sensor(self, device: EdgeOSDeviceData):
        unit_of_measurement = self._get_rate_unit_of_measurement()

        state = self._convert_unit(device.sent.rate)

        self._load_device_stats_sensor(device,
                                       "Sent Rate",
                                       state,
                                       unit_of_measurement,
                                       "mdi:upload-network-outline",
                                       SensorStateClass.MEASUREMENT)

    def _load_device_sent_traffic_sensor(self, device: EdgeOSDeviceData):
        unit_of_measurement = self._get_unit_of_measurement()

        state = self._convert_unit(device.sent.total)

        self._load_device_stats_sensor(device,
                                       "Sent Traffic",
                                       state,
                                       unit_of_measurement,
                                       "mdi:upload-network-outline")

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

            details = device.to_dict()

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

            details = device.to_dict()
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

    def _load_interface_received_rate_sensor(self, interface: EdgeOSInterfaceData):
        unit_of_measurement = self._get_rate_unit_of_measurement()

        state = self._convert_unit(interface.received.rate)

        self._load_interface_stats_sensor(interface,
                                          "Received Rate",
                                          state,
                                          unit_of_measurement,
                                          "mdi:download-network-outline",
                                          SensorStateClass.MEASUREMENT)

    def _load_interface_received_traffic_sensor(self, interface: EdgeOSInterfaceData):
        unit_of_measurement = self._get_unit_of_measurement()

        state = self._convert_unit(interface.received.rate)

        self._load_interface_stats_sensor(interface,
                                          "Received Traffic",
                                          state,
                                          unit_of_measurement,
                                          "mdi:download-network-outline")

    def _load_interface_received_dropped_sensor(self, interface: EdgeOSInterfaceData):
        self._load_interface_stats_sensor(interface,
                                          "Received Dropped",
                                          interface.received.dropped,
                                          TRAFFIC_DATA_DROPPED.capitalize(),
                                          "mdi:package-variant-minus")

    def _load_interface_received_errors_sensor(self, interface: EdgeOSInterfaceData):
        self._load_interface_stats_sensor(interface,
                                          "Received Errors",
                                          interface.received.errors,
                                          TRAFFIC_DATA_ERRORS.capitalize(),
                                          "mdi:timeline-alert")

    def _load_interface_received_packets_sensor(self, interface: EdgeOSInterfaceData):
        self._load_interface_stats_sensor(interface,
                                          "Received Packets",
                                          interface.received.packets,
                                          TRAFFIC_DATA_PACKETS.capitalize(),
                                          "mdi:package-up")

    def _load_interface_sent_rate_sensor(self, interface: EdgeOSInterfaceData):
        unit_of_measurement = self._get_rate_unit_of_measurement()

        state = self._convert_unit(interface.sent.rate)

        self._load_interface_stats_sensor(interface,
                                          "Sent Rate",
                                          state,
                                          unit_of_measurement,
                                          "mdi:upload-network-outline",
                                          SensorStateClass.MEASUREMENT)

    def _load_interface_sent_traffic_sensor(self, interface: EdgeOSInterfaceData):
        unit_of_measurement = self._get_unit_of_measurement()

        state = self._convert_unit(interface.sent.total)

        self._load_interface_stats_sensor(interface,
                                          "Sent Traffic",
                                          state,
                                          unit_of_measurement,
                                          "mdi:upload-network-outline")

    def _load_interface_sent_dropped_sensor(self, interface: EdgeOSInterfaceData):
        self._load_interface_stats_sensor(interface,
                                          "Sent Dropped",
                                          interface.sent.dropped,
                                          TRAFFIC_DATA_DROPPED.capitalize(),
                                          "mdi:package-variant-minus")

    def _load_interface_sent_errors_sensor(self, interface: EdgeOSInterfaceData):
        self._load_interface_stats_sensor(interface,
                                          "Sent Errors",
                                          interface.sent.errors,
                                          TRAFFIC_DATA_ERRORS.capitalize(),
                                          "mdi:timeline-alert")

    def _load_interface_sent_packets_sensor(self, interface: EdgeOSInterfaceData):
        self._load_interface_stats_sensor(interface,
                                          "Sent Packets",
                                          interface.sent.packets,
                                          TRAFFIC_DATA_PACKETS.capitalize(),
                                          "mdi:package-up")

    def _load_device_stats_sensor(self,
                                  device: EdgeOSDeviceData,
                                  entity_suffix: str,
                                  state: str | int | float | None,
                                  unit_of_measurement: str,
                                  icon: str | None,
                                  state_class: SensorStateClass = SensorStateClass.TOTAL_INCREASING):

        device_name = self._get_device_name(device)
        entity_name = f"{device_name} {entity_suffix}"

        is_monitored = self.storage_api.monitored_devices.get(device.unique_id, False)

        self._load_stats_sensor(device_name, entity_name, state, unit_of_measurement, icon, state_class, is_monitored)

    def _load_interface_stats_sensor(self,
                                     interface: EdgeOSInterfaceData,
                                     entity_suffix: str,
                                     state: str | int | float | None,
                                     unit_of_measurement: str,
                                     icon: str | None,
                                     state_class: SensorStateClass = SensorStateClass.TOTAL_INCREASING):

        device_name = self._get_interface_name(interface)
        entity_name = f"{device_name} {entity_suffix}"

        is_monitored = self.storage_api.monitored_interfaces.get(interface.unique_id, False)

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

            details = interface.to_dict()

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

            details = interface.to_dict()

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

        await self.async_update(datetime.now())

    async def _set_interface_unmonitored(self, entity: EntityData):
        interface_item = self._get_interface_from_entity(entity)

        await self.storage_api.set_monitored_interface(interface_item.unique_id, False)

        await self.async_update(datetime.now())

    async def _set_device_monitored(self, entity: EntityData):
        device_item = self._get_device_from_entity(entity)

        await self.storage_api.set_monitored_device(device_item.unique_id, True)

        await self.async_update(datetime.now())

    async def _set_device_unmonitored(self, entity: EntityData):
        device_item = self._get_device_from_entity(entity)

        await self.storage_api.set_monitored_device(device_item.unique_id, False)

        await self.async_update(datetime.now())

    async def _enable_log_incoming_messages(self, entity: EntityData):
        await self.storage_api.set_log_incoming_messages(True)

    async def _disable_log_incoming_messages(self, entity: EntityData):
        await self.storage_api.set_log_incoming_messages(False)

    async def _enable_store_debug_data(self, entity: EntityData):
        await self.storage_api.set_store_debug_data(True)

    async def _disable_store_debug_data(self, entity: EntityData):
        await self.storage_api.set_store_debug_data(False)

    async def _set_unit(self, entity: EntityData, option: str):
        await self.storage_api.set_unit(option)

        await self.async_update(datetime.now())

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
    def _format_number(value: int | float, digits: int = 0) -> int | float:
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
        data = service_call.data
        device_id = data.get("device_id")
        store_debug_data = data.get(STORAGE_DATA_STORE_DEBUG_DATA)
        unit = data.get(STORAGE_DATA_UNIT)
        consider_away_interval = data.get(STORAGE_DATA_CONSIDER_AWAY_INTERVAL)
        log_incoming_messages = data.get(STORAGE_DATA_LOG_INCOMING_MESSAGES)

        _LOGGER.info(f"Update configuration called with data: {data}")

        if device_id is None:
            _LOGGER.error("Operation cannot be performed, missing device information")

        else:
            dr = async_get_device_registry(self._hass)
            device = dr.devices.get(device_id)
            can_handle_device = self.entry_id in device.config_entries
            should_reload_integration = False

            if can_handle_device:
                if store_debug_data is not None and self.storage_api.store_debug_data != store_debug_data:
                    await self.storage_api.set_store_debug_data(store_debug_data)

                if unit is not None and self.storage_api.unit != unit:
                    await self.storage_api.set_unit(unit)

                    should_reload_integration = True

                if consider_away_interval is not None and \
                        self.storage_api.consider_away_interval != consider_away_interval:

                    await self.storage_api.set_consider_away_interval(consider_away_interval)

                    should_reload_integration = True

                current_log_incoming_messages = self.storage_api.log_incoming_messages
                if log_incoming_messages is not None and current_log_incoming_messages != log_incoming_messages:
                    await self.storage_api.set_log_incoming_messages(log_incoming_messages)

            if should_reload_integration:
                await self._reload_integration()

    @staticmethod
    def _get_last_reset(uptime):
        now = datetime.now().timestamp()
        last_reset = int(now) - uptime

        result = datetime.fromtimestamp(last_reset)

        return result
