"""
This component provides support for Home Automation Manager (HAM).
For more details about this component, please refer to the documentation at
https://home-assistant.io/components/edgeos/
"""
from asyncio import sleep
import logging
import sys
from typing import Optional

from ..clients.web_api import EdgeOSWebAPI
from ..clients.web_socket import EdgeOSWebSocket
from ..helpers.const import *
from ..models.config_data import ConfigData
from ..models.exceptions import IncompatibleVersion, SessionTerminatedException
from .configuration_manager import ConfigManager
from .version_check import VersionManager

_LOGGER = logging.getLogger(__name__)


class EdgeOSData:
    hostname: str
    version: str
    edgeos_data: dict
    system_data: dict
    version_manager: VersionManager

    def __init__(self, hass, config_manager: ConfigManager, update_home_assistant):
        self._hass = hass
        self._update_home_assistant = update_home_assistant
        self._config_manager = config_manager

        self._is_initialized = False
        self._is_updating = False

        self.edgeos_data = {}
        self.system_data = {}

        self._ws_handlers = self.get_ws_handlers()

        config_data = self._config_manager.data

        topics = self._ws_handlers.keys()

        self.hostname = config_data.host

        self._ws = EdgeOSWebSocket(self._hass, config_manager, topics, self.ws_handler)

        self._api = EdgeOSWebAPI(
            self._hass, config_manager, self.edgeos_disconnection_handler, self._ws
        )

        self.version_manager = VersionManager()

        self._is_active = True

    @property
    def version(self):
        return self.version_manager.version

    @property
    def product(self):
        return self._api.product

    @property
    def config_data(self) -> Optional[ConfigData]:
        if self._config_manager is not None:
            return self._config_manager.data

        return None

    def disconnect(self):
        self._ws.disconnect()

    async def initialize(self, post_login_action=None):
        try:
            is_first_time = True

            while self._is_active:
                if is_first_time:
                    is_first_time = False

                else:
                    slept = False

                    try:
                        _LOGGER.debug(
                            f"Sleeping {RECONNECT_INTERVAL} seconds until next reconnect attempt"
                        )

                        await sleep(RECONNECT_INTERVAL)
                        slept = True

                    finally:
                        if not slept:
                            return

                if self._is_active:
                    await self._initialize(post_login_action)

                post_login_action = None

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            if ex is not None or self._is_active:
                _LOGGER.error(
                    f"Failed to initialize EdgeOS Manager, Error: {ex}, Line: {line_number}"
                )

    async def _initialize(self, post_login_action=None):
        try:
            _LOGGER.debug(f"Initializing API")
            await self._api.initialize()

            if await self._api.login():
                _LOGGER.debug(f"Requesting initial data")
                await self.refresh()

                if post_login_action is not None:
                    await post_login_action()

                cookies = self._api.cookies_data
                session_id = self._api.session_id

                self.version_manager.validate()

                _LOGGER.debug(f"Initializing WS using session: {session_id}")
                await self._ws.initialize(cookies, session_id)

        except SessionTerminatedException as stex:
            _LOGGER.info(f"Session terminated ({stex})")

            self._is_active = False

        except IncompatibleVersion as ivex:
            _LOGGER.error(str(ivex))

            self._is_active = False

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(
                f"Failed to initialize EdgeOS Manager, Error: {str(ex)}, Line: {line_number}"
            )

    @property
    def is_initialized(self):
        return self._is_initialized

    async def edgeos_disconnection_handler(self):
        _LOGGER.debug(f"Disconnection detected, reconnecting...")

        await self.terminate()

        await self.initialize()

    async def terminate(self):
        try:
            _LOGGER.debug(f"Terminating WS")

            self._is_active = False

            await self._ws.close()

            _LOGGER.debug(f"WS terminated")
        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(
                f"Failed to terminate connection to WS, Error: {ex}, Line: {line_number}"
            )

    async def async_send_heartbeat(self):
        if not self._api.is_initialized:
            self.disconnect()

        result = await self._api.async_send_heartbeat()

        if result:
            await self._ws.async_send_heartbeat()

    async def refresh(self):
        try:
            if not self._api.is_initialized:
                self.disconnect()

                return

            _LOGGER.debug("Getting devices by API")

            devices_data = await self._api.get_devices_data()

            if devices_data is not None:
                system_info_data = await self._api.get_general_data(SYS_INFO_KEY)

                if system_info_data is not None:
                    self.load_system_data(devices_data, system_info_data)

                self.load_devices(devices_data)
                self.load_interfaces(devices_data)

                unknown_devices_data = await self._api.get_general_data(DHCP_LEASES_KEY)

                if unknown_devices_data is not None:
                    self.load_unknown_devices(unknown_devices_data)

            self.update()

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(
                f"Failed to load devices data, Error: {ex}, Line: {line_number}"
            )

    def update(self):
        try:
            devices = self.get_devices()
            interfaces = self.get_interfaces()
            system_state = self.get_system_state()
            unknown_devices = self.get_unknown_devices()

            api_last_update = self._api.last_update
            web_socket_last_update = self._ws.last_update

            if system_state is None:
                system_state = {}

            system_state[IS_ALIVE] = self._api.is_connected

            self.system_data = {
                INTERFACES_KEY: interfaces,
                STATIC_DEVICES_KEY: devices,
                UNKNOWN_DEVICES_KEY: unknown_devices,
                SYSTEM_STATS_KEY: system_state,
                ATTR_API_LAST_UPDATE: api_last_update,
                ATTR_WEB_SOCKET_LAST_UPDATE: web_socket_last_update,
            }

            self._update_home_assistant()
        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(f"Failed to refresh data, Error: {ex}, Line: {line_number}")

    def ws_handler(self, payload=None):
        try:
            if payload is not None:
                for key in payload:
                    _LOGGER.debug(f"Running parser of {key}")

                    data = payload.get(key)
                    handler = self._ws_handlers.get(key)

                    if handler is None:
                        _LOGGER.error(f"Handler not found for {key}")
                    else:
                        handler(data)

                        self.update()
        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(
                f"Failed to handle WS message, Error: {ex}, Line: {line_number}"
            )

    def get_ws_handlers(self) -> dict:
        ws_handlers = {
            EXPORT_KEY: self.handle_export,
            INTERFACES_KEY: self.handle_interfaces,
            SYSTEM_STATS_KEY: self.handle_system_stats,
            DISCOVER_KEY: self.handle_discover,
        }

        return ws_handlers

    def load_unknown_devices(self, unknown_devices_data):
        try:
            if unknown_devices_data is not None:
                result = []

                dhcp_server_leases_data = unknown_devices_data.get(
                    "dhcp-server-leases", {}
                )

                for interface_key in dhcp_server_leases_data:
                    interface_info = dhcp_server_leases_data[interface_key]

                    for ip in interface_info:
                        device_info = interface_info[ip]

                        device = {
                            "ip": ip,
                            "expiration": device_info.get("expiration"),
                            "pool": device_info.get("pool"),
                            "mac": device_info.get("mac"),
                            "client-hostname": device_info.get("client-hostname"),
                        }

                        result.append(device)

                self.set_unknown_devices(result)

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(
                f"Failed to load devices data, Error: {ex}, Line: {line_number}"
            )

    def load_devices(self, device_data):
        if device_data is None:
            return

        service_data = device_data.get(SERVICE, {})
        dhcp_server_data = service_data.get(DHCP_SERVER, {})
        shared_network_data = dhcp_server_data.get(SHARED_NETWORK_NAME, {})

        for shared_network_key in shared_network_data:
            shared_network_item = shared_network_data[shared_network_key]
            subnet_data = shared_network_item.get(SUBNET, {})
            for subnet_key in subnet_data:
                subnet_item = subnet_data[subnet_key]

                static_mapping_data = subnet_item.get(STATIC_MAPPING, {})
                for hostname in static_mapping_data:
                    device = self.get_device(hostname)

                    static_mapping_item = static_mapping_data[hostname]
                    ip = static_mapping_item.get(IP_ADDRESS)
                    mac = static_mapping_item.get(MAC_ADDRESS)

                    name = hostname
                    if ip is not None:
                        name = f"{hostname} ({ip})"

                    device[IP] = ip
                    device[MAC] = mac
                    device[ATTR_NAME] = name

                    self.check_last_activity(device)

                    self.set_device(hostname, device)

    def load_interfaces(self, device_data):
        if device_data is None:
            return

        interfaces_data = device_data.get(INTERFACES_KEY, {})
        ethernet_data = interfaces_data.get("ethernet", {})

        for ethernet_key in ethernet_data:
            ethernet_item = ethernet_data[ethernet_key]
            description = ethernet_item.get("description")

            name = ethernet_key

            if description is not None:
                name = f"{ethernet_key} ({description})"

            interface = {ATTR_NAME: name}

            self.set_interface(ethernet_key, interface)

    def load_system_data(self, devices_data, system_info_data):
        if devices_data is None or system_info_data is None:
            return

        system_data = devices_data.get("system", {})
        self.hostname = system_data.get("host-name", self.hostname)
        self.version_manager.update(system_info_data)

    def handle_interfaces(self, data):
        try:
            _LOGGER.debug(f"Handle {INTERFACES_KEY} data")

            if data is None or data == "":
                _LOGGER.debug(f"{INTERFACES_KEY} is empty")
                return

            for name in data:
                interface_data = data.get(name)

                interface = {}

                for item in interface_data:
                    item_data = interface_data.get(item)

                    if ADDRESS_LIST == item:
                        interface[item] = item_data

                    elif INTERFACES_STATS == item:
                        for stats_item in INTERFACES_STATS_MAP:
                            interface[stats_item] = item_data.get(stats_item)

                    else:
                        if item in INTERFACES_MAIN_MAP:
                            interface[item] = item_data

                self.set_interface(name, interface)
        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(
                f"Failed to load {INTERFACES_KEY}, Error: {ex}, Line: {line_number}"
            )

    def handle_system_stats(self, data):
        try:
            _LOGGER.debug(f"Handle {SYSTEM_STATS_KEY} data")

            if data is None or data == "":
                _LOGGER.debug(f"{SYSTEM_STATS_KEY} is empty")
                return

            self.set_system_state(data)
        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(
                f"Failed to load {SYSTEM_STATS_KEY}, Error: {ex}, Line: {line_number}"
            )

    def handle_discover(self, data):
        try:
            _LOGGER.debug(f"Handle {DISCOVER_KEY} data")

            result = self.get_discover_data()

            if data is None or data == "":
                _LOGGER.debug(f"{DISCOVER_KEY} is empty")
                return

            devices_data = data.get(DEVICE_LIST, [])

            for device_data in devices_data:
                for key in DISCOVER_DEVICE_ITEMS:
                    device_data_item = device_data.get(key, {})

                    if key == ADDRESS_LIST:
                        discover_addresses = {}

                        for address in device_data_item:
                            hwaddr = address.get(ADDRESS_HWADDR)
                            ipv4 = address.get(ADDRESS_IPV4)

                            discover_addresses[hwaddr] = ipv4

                        result[key] = discover_addresses
                    else:
                        result[key] = device_data_item

            self.set_discover_data(result)
        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(
                f"Failed to load {DISCOVER_KEY}, Original Message: {data}, Error: {ex}, Line: {line_number}"
            )

    def check_last_activity(self, device):
        date_minimum = datetime.fromtimestamp(0)
        device_ip = device.get(IP)
        device_connected = device.get(CONNECTED, False)
        device_last_activity = device.get(LAST_ACTIVITY, date_minimum)

        is_connected = False

        time_since_last_action = (datetime.now() - device_last_activity).total_seconds()

        if time_since_last_action < self.config_data.consider_away_interval:
            is_connected = True
        else:
            if (
                device_connected != is_connected
                and device_last_activity != date_minimum
            ):
                msg = [
                    f"Device {device_ip} disconnected",
                    f"due to inactivity since {device_last_activity}",
                    f"({time_since_last_action} seconds)",
                ]

                _LOGGER.info(" ".join(msg))

        device[CONNECTED] = is_connected

    def handle_export(self, data):
        try:
            _LOGGER.debug(f"Handle {EXPORT_KEY} data")

            if data is None or data == "":
                _LOGGER.debug(f"{EXPORT_KEY} is empty")
                return

            all_devices = self.get_devices().keys()

            for hostname in all_devices:
                device = self.get_device(hostname)
                device_ip = device.get(IP)
                device_data = data.get(device_ip)

                if device_data is not None:
                    traffic: dict = {}

                    for item in DEVICE_SERVICES_STATS_MAP:
                        traffic[item] = int(0)

                    for service in device_data:
                        service_data = device_data.get(service, {})
                        for item in service_data:
                            current_value = traffic.get(item, 0)
                            service_data_item_value = 0

                            if item in service_data and service_data[item] != "":
                                service_data_item_value = int(service_data[item])

                            if "x_rate" in item and service_data_item_value > 0:
                                device[LAST_ACTIVITY] = datetime.now()

                            traffic_value = current_value + service_data_item_value

                            traffic[item] = traffic_value
                            device[item] = traffic_value

                self.check_last_activity(device)

                self.set_device(hostname, device)

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(
                f"Failed to load {EXPORT_KEY}, Error: {ex}, Line: {line_number}"
            )

    def _get_edgeos_data(self, key):
        if key not in self.edgeos_data:
            self.edgeos_data[key] = {}

        result = self.edgeos_data[key]

        return result

    def _set_edgeos_data(self, key, data):
        self.edgeos_data[key] = data

    def set_discover_data(self, discover_state):
        self._set_edgeos_data(DISCOVER_KEY, discover_state)

    def get_discover_data(self):
        result = self._get_edgeos_data(DISCOVER_KEY)

        return result

    def set_unknown_devices(self, unknown_devices):
        self._set_edgeos_data(UNKNOWN_DEVICES_KEY, unknown_devices)

    def get_unknown_devices(self):
        result = self._get_edgeos_data(UNKNOWN_DEVICES_KEY)

        return result

    def set_system_state(self, system_state):
        self._set_edgeos_data(SYSTEM_STATS_KEY, system_state)

    def get_system_state(self):
        result = self._get_edgeos_data(SYSTEM_STATS_KEY)

        return result

    def set_interface(self, name, interface):
        all_interfaces = self.get_interfaces()

        if name not in all_interfaces:
            all_interfaces[name] = {}

        current_interface = all_interfaces[name]

        for key in interface:
            current_interface[key] = interface[key]

    def get_interfaces(self):
        result = self._get_edgeos_data(INTERFACES_KEY)

        return result

    def get_interface(self, name):
        interfaces = self.get_interfaces()
        interface = interfaces.get(name, {})

        return interface

    def get_devices(self):
        result = self._get_edgeos_data(STATIC_DEVICES_KEY)

        return result

    def set_device(self, hostname, device):
        all_devices = self.get_devices()

        if hostname is not None:
            if hostname not in all_devices:
                all_devices[hostname] = {}

            current_device = all_devices[hostname]

            for key in device:
                current_device[key] = device[key]

    def get_device(self, hostname):
        devices = self.get_devices()
        device = devices.get(hostname, {})

        return device

    @staticmethod
    def get_device_name(hostname):
        name = f"{DEFAULT_NAME} {hostname}"

        return name

    def get_device_mac(self, hostname):
        device = self.get_device(hostname)

        mac = device.get(MAC)

        return mac

    def is_device_online(self, hostname) -> bool:
        device = self.get_device(hostname)

        connected = device.get(CONNECTED, False)

        return connected
