"""
This component provides support for Home Automation Manager (HAM).
For more details about this component, please refer to the documentation at
https://home-assistant.io/components/edgeos/
"""
import sys
import logging
import voluptuous as vol
from datetime import datetime

from homeassistant.const import (CONF_USERNAME, CONF_PASSWORD, CONF_SSL, CONF_HOST)

from homeassistant.helpers import config_validation as cv

from .const import VERSION
from .const import *
from .home_assistant import (EdgeOSHomeAssistant)
from .mocked_home_assistant import (EdgeOSMockedHomeAssistant)
from .web_api import (EdgeOSWebAPI)
from .web_login import (EdgeOSWebLogin)
from .web_socket import (EdgeOSWebSocket)

REQUIREMENTS = ['aiohttp']

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_HOST): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Optional(CONF_USERNAME, default=DEFAULT_USERNAME): cv.string,
        vol.Optional(CONF_SSL, default=False): cv.boolean,
        vol.Optional(CONF_CERT_FILE, default=''): cv.string,
        vol.Optional(CONF_MONITORED_INTERFACES, default=[]): vol.All(cv.ensure_list, [cv.string]),
        vol.Optional(CONF_MONITORED_DEVICES, default=[]): vol.All(cv.ensure_list, [cv.string]),
        vol.Optional(CONF_UNIT, default=ATTR_BYTE): vol.In(ALLOWED_UNITS)
    }),
}, extra=vol.ALLOW_EXTRA)


def setup(hass, config):
    """Set up an Home Automation Manager component."""
    conf = config.get(DOMAIN, {})

    is_ssl = conf.get(CONF_SSL, False)
    host = conf.get(CONF_HOST)
    username = conf.get(CONF_USERNAME, DEFAULT_USERNAME)
    password = conf.get(CONF_PASSWORD)
    monitored_interfaces = conf.get(CONF_MONITORED_INTERFACES, [])
    monitored_devices = conf.get(CONF_MONITORED_DEVICES, [])
    unit = conf.get(CONF_UNIT, ATTR_BYTE)
    scan_interval = SCAN_INTERVAL

    data = EdgeOS(hass, host, username, password, is_ssl, monitored_interfaces,
                  monitored_devices, unit, scan_interval)

    hass.data[DATA_EDGEOS] = data

    return data.is_initialized


class EdgeOS:
    def __init__(self, hass, host, username, password, is_ssl, monitored_interfaces,
                 monitored_devices, unit, scan_interval, is_mocked=False):

        self._initialization_counter = -1
        self._is_initialized = False
        self._host = host
        self._is_ssl = is_ssl
        self._username = username
        self._password = password
        self._hass = hass

        protocol = PROTOCOL_UNSECURED
        if is_ssl:
            protocol = PROTOCOL_SECURED

        self._edgeos_url = API_URL_TEMPLATE.format(protocol, host)

        self._edgeos_data = {}

        self._ws_handlers = self.get_ws_handlers()
        self._topics = self._ws_handlers.keys()

        self._api = EdgeOSWebAPI(hass, self._edgeos_url, self.edgeos_disconnection_handler)

        self._ws = EdgeOSWebSocket(hass,
                                   self._edgeos_url,
                                   self._topics,
                                   self.ws_handler)

        self._edgeos_login_service = EdgeOSWebLogin(self._host, self._is_ssl, self._username, self._password)

        if is_mocked:
            self._edgeos_ha = EdgeOSMockedHomeAssistant(hass, monitored_interfaces, monitored_devices, unit, scan_interval)
        else:
            self._edgeos_ha = EdgeOSHomeAssistant(hass, monitored_interfaces, monitored_devices, unit, scan_interval)

        async def edgeos_initialize(*args, **kwargs):
            _LOGGER.info(f'Starting EdgeOS')

            await self.start()

        async def edgeos_stop(*args, **kwargs):
            _LOGGER.info(f'Stopping EdgeOS')

            await self.terminate()

        async def edgeos_refresh(event_time):
            _LOGGER.debug(f'Refreshing EdgeOS ({str(event_time)})')

            await self.refresh_data()

        def edgeos_save_debug_data(service):
            _LOGGER.info(f'Save EdgeOS debug data')

            self._edgeos_ha.store_data(self._edgeos_data)

        def edgeos_log_events(service):
            _LOGGER.info(f'Log Events EdgeOS WebSocket')

            enabled = service.data.get(ATTR_ENABLED, False)

            self._ws.log_events(enabled)

        try:
            if self._edgeos_login_service.login():
                self._edgeos_ha.initialize(edgeos_initialize,
                                           edgeos_stop,
                                           edgeos_refresh,
                                           edgeos_save_debug_data,
                                           edgeos_log_events)

                self._is_initialized = True
        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            self._edgeos_ha.notify_error(ex, line_number)

    @property
    def is_initialized(self):
        return self._is_initialized

    async def edgeos_disconnection_handler(self):
        _LOGGER.debug(f'Disconnection detected, reconnecting...')

        await self.terminate()

        if self._edgeos_login_service.login():
            await self.start()

    async def terminate(self):
        try:
            _LOGGER.debug(f'Terminating WS')

            await self._ws.close()

            _LOGGER.debug(f'WS terminated')
        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(f"Failed to terminate connection to WS, Error: {ex}, Line: {line_number}")

    async def start(self):
        try:
            cookies = self._edgeos_login_service.cookies_data
            session_id = self._edgeos_login_service.session_id

            _LOGGER.debug(f'Initializing API')

            await self._api.initialize(cookies)

            _LOGGER.debug(f'Requesting initial data')
            await self.refresh_data()

            _LOGGER.debug(f'Initializing WS using session: {session_id}')
            await self._ws.initialize(cookies, session_id)
        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(f'Failed to start EdgeOS, Error: {ex}, Line: {line_number}')

    async def refresh_data(self):
        try:
            await self._api.heartbeat()
            await self.load_devices_data()

            devices = self.get_devices()
            interfaces = self.get_interfaces()
            system_state = self.get_system_state()
            unknown_devices = self.get_unknown_devices()

            api_last_update = self._api.last_update
            web_socket_last_update = self._ws.last_update

            if system_state is not None:
                system_state[IS_ALIVE] = self._api.is_connected

            self._edgeos_ha.update(interfaces, devices, unknown_devices, system_state,
                                   api_last_update, web_socket_last_update)
        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(f'Failed to refresh data, Error: {ex}, Line: {line_number}')

    def ws_handler(self, payload=None):
        try:
            if payload is not None:
                for key in payload:
                    _LOGGER.debug(f"Running parser of {key}")

                    data = payload.get(key)
                    handler = self._ws_handlers.get(key)

                    if handler is None:
                        _LOGGER.error(f'Handler not found for {key}')
                    else:
                        handler(data)
        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(f'Failed to handle WS message, Error: {ex}, Line: {line_number}')

    def get_ws_handlers(self):
        ws_handlers = {
            EXPORT_KEY: self.handle_export,
            INTERFACES_KEY: self.handle_interfaces,
            SYSTEM_STATS_KEY: self.handle_system_stats,
            DISCOVER_KEY: self.handle_discover
        }

        return ws_handlers

    async def load_devices_data(self):
        try:
            _LOGGER.debug('Getting devices by API')

            result = {}

            previous_result = self.get_devices()
            if previous_result is None:
                previous_result = {}

            devices_data = await self._api.get_devices_data()

            if devices_data is not None:
                service_data = devices_data.get(SERVICE, {})

                if isinstance(service_data, dict):
                    dhcp_server_data = service_data.get(DHCP_SERVER, {})
                    shared_network_name_data = dhcp_server_data.get(SHARED_NETWORK_NAME, {})

                    for shared_network_name_key in shared_network_name_data:
                        dhcp_network_allocation = shared_network_name_data.get(shared_network_name_key, {})
                        subnet = dhcp_network_allocation.get(SUBNET, {})

                        for subnet_mask_key in subnet:
                            subnet_mask = subnet.get(subnet_mask_key, {})
                            static_mapping = subnet_mask.get(STATIC_MAPPING, {})

                            for host_name in static_mapping:
                                host_data = static_mapping.get(host_name, {})
                                host_ip = host_data.get(IP_ADDRESS)
                                host_mac = host_data.get(MAC_ADDRESS)

                                data = {
                                    IP: host_ip,
                                    MAC: host_mac
                                }

                                previous_host_data = previous_result.get(host_name, {})

                                for previous_key in previous_host_data:
                                    data[previous_key] = previous_host_data.get(previous_key)

                                result[host_name] = data

                    self.set_devices(result)
                else:
                    _LOGGER.warning(f"Invalid Service Data: {service_data}")
        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(f'Failed to load devices data, Error: {ex}, Line: {line_number}')

    def handle_interfaces(self, data):
        try:
            _LOGGER.debug(f'Handle {INTERFACES_KEY} data')

            if data is None or data == '':
                _LOGGER.debug(f'{INTERFACES_KEY} is empty')
                return

            result = self.get_interfaces()

            for interface in data:
                interface_data = None

                if interface in data:
                    interface_data = data.get(interface)

                interface_data_item = self.get_interface_data(interface_data)

                result[interface] = interface_data_item

            self.set_interfaces(result)
        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(f'Failed to load {INTERFACES_KEY}, Error: {ex}, Line: {line_number}')

    @staticmethod
    def get_interface_data(interface_data):
        result = {}

        for item in interface_data:
            data = interface_data.get(item)

            if ADDRESS_LIST == item:
                result[item] = data

            elif INTERFACES_STATS == item:
                for stats_item in INTERFACES_STATS_MAP:
                    result[stats_item] = data.get(stats_item)

            else:
                if item in INTERFACES_MAIN_MAP:
                    result[item] = data

        return result

    def handle_system_stats(self, data):
        try:
            _LOGGER.debug(f'Handle {SYSTEM_STATS_KEY} data')

            if data is None or data == '':
                _LOGGER.debug(f'{SYSTEM_STATS_KEY} is empty')
                return

            self.set_system_state(data)
        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(f'Failed to load {SYSTEM_STATS_KEY}, Error: {ex}, Line: {line_number}')

    def handle_discover(self, data):
        try:
            _LOGGER.debug(f'Handle {DISCOVER_KEY} data')

            result = self.get_discover_data()

            if data is None or data == '':
                _LOGGER.debug(f'{DISCOVER_KEY} is empty')
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

            _LOGGER.error(f'Failed to load {DISCOVER_KEY}, Original Message: {data}, Error: {ex}, Line: {line_number}')

    def handle_export(self, data):
        try:
            _LOGGER.debug(f'Handle {EXPORT_KEY} data')

            if data is None or data == '':
                _LOGGER.debug(f'{EXPORT_KEY} is empty')
                return

            result = self.get_devices()

            for hostname in result:
                host_data = result.get(hostname, {})

                if IP in host_data:
                    host_data_ip = host_data.get(IP)

                    if host_data_ip in data:

                        host_data_traffic = {}
                        for item in DEVICE_SERVICES_STATS_MAP:
                            host_data_traffic[item] = int(0)

                        device_data = data.get(host_data_ip, {})
                        last_activity = host_data.get(LAST_ACTIVITY)

                        if last_activity is not None:
                            diff = (datetime.now() - last_activity).total_seconds()

                            if diff >= DISCONNECTED_INTERVAL:
                                last_activity = None

                        for service in device_data:
                            service_data = device_data.get(service, {})
                            for item in service_data:
                                current_value = 0
                                service_data_item_value = 0

                                if item in host_data_traffic and host_data_traffic[item] != '':
                                    current_value = int(host_data_traffic[item])

                                if item in service_data and service_data[item] != '':
                                    service_data_item_value = int(service_data[item])

                                if item in ['tx_rate'] and current_value > 0:
                                    last_activity = datetime.now()

                                host_data_traffic[item] = current_value + service_data_item_value

                        for traffic_data_item in host_data_traffic:
                            host_data[traffic_data_item] = host_data_traffic.get(traffic_data_item)

                        is_connected = FALSE_STR

                        if last_activity is not None:
                            host_data[LAST_ACTIVITY] = last_activity

                            diff = (datetime.now() - last_activity).total_seconds()

                            if diff < DISCONNECTED_INTERVAL:
                                is_connected = TRUE_STR

                        host_data[CONNECTED] = is_connected

                        del data[host_data_ip]
                    else:
                        host_data[CONNECTED] = FALSE_STR

            unknown_devices = []
            for host_ip in data:
                unknown_devices.append(host_ip)

            self.set_devices(result)
            self.set_unknown_devices(unknown_devices)
        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(f'Failed to load {EXPORT_KEY}, Error: {ex}, Line: {line_number}')

    def set_discover_data(self, discover_state):
        self._edgeos_data[DISCOVER_KEY] = discover_state

    def get_discover_data(self):
        result = self._edgeos_data.get(DISCOVER_KEY, {})

        return result

    def set_unknown_devices(self, unknown_devices):
        self._edgeos_data[UNKNOWN_DEVICES_KEY] = unknown_devices

    def get_unknown_devices(self):
        result = self._edgeos_data.get(UNKNOWN_DEVICES_KEY, {})

        return result

    def set_system_state(self, system_state):
        self._edgeos_data[SYSTEM_STATS_KEY] = system_state

    def get_system_state(self):
        result = self._edgeos_data.get(SYSTEM_STATS_KEY, {})

        return result

    def set_interfaces(self, interfaces):
        self._edgeos_data[INTERFACES_KEY] = interfaces

    def get_interfaces(self):
        result = self._edgeos_data.get(INTERFACES_KEY, {})

        return result

    def set_devices(self, devices):
        self._edgeos_data[STATIC_DEVICES_KEY] = devices

    def get_devices(self):
        result = self._edgeos_data.get(STATIC_DEVICES_KEY, {})

        return result

    def get_device(self, hostname):
        devices = self.get_devices()
        device = devices.get(hostname, {})

        return device

    @staticmethod
    def get_device_name(hostname):
        name = f'{DEFAULT_NAME} {hostname}'

        return name

    def get_device_mac(self, hostname):
        device = self.get_device(hostname)

        mac = device.get(MAC)

        return mac

    def is_device_online(self, hostname):
        device = self.get_device(hostname)

        connected = device.get(CONNECTED, FALSE_STR)

        if connected == TRUE_STR:
            is_online = True
        else:
            is_online = False

        return is_online
