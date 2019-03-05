"""
This component provides support for Home Automation Manager (HAM).
For more details about this component, please refer to the documentation at
https://home-assistant.io/components/edgeos/
"""
import re
import sys
import logging
import requests
from time import sleep
from datetime import datetime, timedelta
import json
from urllib.parse import urlparse
import urllib3
import aiohttp
import asyncio
import voluptuous as vol

from homeassistant.const import (CONF_USERNAME, CONF_PASSWORD, EVENT_HOMEASSISTANT_START, CONF_SSL, CONF_HOST,
                                 EVENT_HOMEASSISTANT_STOP, STATE_OFF, STATE_ON, ATTR_FRIENDLY_NAME, HTTP_OK,
                                 STATE_UNKNOWN, ATTR_NAME, ATTR_UNIT_OF_MEASUREMENT, EVENT_TIME_CHANGED)

from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.event import track_time_interval

from homeassistant.util import slugify

from .const import *

REQUIREMENTS = ['aiohttp']

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=60)
EMPTY_LAST_VALID = datetime.fromtimestamp(100000)

INTERFACES_MAIN_MAP = {
    LINK_UP: {ATTR_NAME: 'Connected', ATTR_UNIT_OF_MEASUREMENT: 'Connectivity'},
    'speed': {ATTR_NAME: 'Link Speed (Mbps)'},
    'duplex': {ATTR_NAME: 'Duplex'},
    'mac': {ATTR_NAME: 'MAC'},
}

INTERFACES_STATS_MAP = {
    'rx_packets': {ATTR_NAME: 'Packets (Received)'},
    'tx_packets': {ATTR_NAME: 'Packets (Sent)'},
    'rx_bytes': {ATTR_NAME: '{}Bytes (Received)', ATTR_UNIT_OF_MEASUREMENT: 'Bytes'},
    'tx_bytes': {ATTR_NAME: '{}Bytes (Sent)', ATTR_UNIT_OF_MEASUREMENT: 'Bytes'},
    'rx_errors': {ATTR_NAME: 'Errors (Received)'},
    'tx_errors': {ATTR_NAME: 'Errors (Sent)'},
    'rx_dropped': {ATTR_NAME: 'Dropped Packets (Received)'},
    'tx_dropped': {ATTR_NAME: 'Dropped Packets (Sent)'},
    'rx_bps': {ATTR_NAME: '{}Bps (Received)', ATTR_UNIT_OF_MEASUREMENT: 'Bps'},
    'tx_bps': {ATTR_NAME: '{}Bps (Sent)', ATTR_UNIT_OF_MEASUREMENT: 'Bps'},
    'multicast': {ATTR_NAME: 'Multicast'}
}

DEVICE_SERVICES_STATS_MAP = {
    'rx_bytes': {ATTR_NAME: '{}Bytes (Received)', ATTR_UNIT_OF_MEASUREMENT: 'Bytes'},
    'tx_bytes': {ATTR_NAME: '{}Bytes (Sent)', ATTR_UNIT_OF_MEASUREMENT: 'Bytes'},
    'rx_rate': {ATTR_NAME: '{}Bps (Received)', ATTR_UNIT_OF_MEASUREMENT: 'Bps'},
    'tx_rate': {ATTR_NAME: '{}Bps (Sent)', ATTR_UNIT_OF_MEASUREMENT: 'Bps'},
}

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
    try:
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

        return True
    except Exception as ex:
        exc_type, exc_obj, tb = sys.exc_info()
        line_number = tb.tb_lineno

        _LOGGER.error(f'Error while initializing EdgeOS, exception: {ex}, Line: {line_number}')

        hass.components.persistent_notification.create(
            f'Error: {ex}<br /> You will need to restart hass after fixing.',
            title=NOTIFICATION_TITLE,
            notification_id=NOTIFICATION_ID)

        return False


class EdgeOS:
    def __init__(self, hass, host, username, password, is_ssl, monitored_interfaces,
                 monitored_devices, unit, scan_interval):

        self._hass = hass
        self._monitored_interfaces = monitored_interfaces
        self._monitored_devices = monitored_devices
        self._is_ssl = is_ssl
        self._host = host

        protocol = PROTOCOL_UNSECURED
        if self._is_ssl:
            protocol = PROTOCOL_SECURED

        self._last_valid = EMPTY_LAST_VALID
        self._edgeos_url = API_URL_TEMPLATE.format(protocol, self._host)

        self._edgeos_data = {}

        self._special_handlers = None
        self._ws_handlers = self.get_ws_handlers()
        self._topics = self._ws_handlers.keys()

        self._ws = None
        self._api = None
        self._session = None

        self._edgeos_login_service = EdgeOSWebLogin(host, is_ssl, username, password)
        self._edgeos_ha = EdgeOSHomeAssistant(hass, monitored_interfaces, monitored_devices, unit)

        async def edgeos_initialize(event_time):
            _LOGGER.info(f'Initialization begun at {event_time}')

            try:
                self.load_connectors()

                await self.refresh_data()

                await self._ws.initialize()
            except Exception as ex:
                exc_type, exc_obj, tb = sys.exc_info()
                line_number = tb.tb_lineno

                _LOGGER.error(f'Failed to run edgeos_initialize, Error: {ex}, Line: {line_number}')

        async def edgeos_stop(event_time):
            _LOGGER.info(f'Stop begun at {event_time}')

            self._ws.stop()

            if self._session is not None:
                await self._session.close()

        async def edgeos_restart(event_time):
            _LOGGER.info(f'Restart begun at {event_time}')

            await edgeos_stop(event_time)
            await edgeos_initialize(event_time)

        async def edgeos_refresh(event_time):
            _LOGGER.info(f'Refresh EdgeOS components ({event_time})')

            await self.refresh_data()

        def edgeos_save_debug_data(event_time):
            _LOGGER.info(f'Save EdgeOS debug data ({event_time})')

            self.log_edgeos_data()

        if self._edgeos_login_service.login():
            hass.services.register(DOMAIN, 'stop', edgeos_stop)
            hass.services.register(DOMAIN, 'restart', edgeos_restart)
            hass.services.register(DOMAIN, 'save_debug_data', edgeos_save_debug_data)

            track_time_interval(hass, edgeos_refresh, scan_interval)

            hass.bus.listen_once(EVENT_HOMEASSISTANT_START, edgeos_initialize)
            hass.bus.listen_once(EVENT_HOMEASSISTANT_STOP, edgeos_stop)

    def load_connectors(self):
        cookies = self._edgeos_login_service.cookies_data

        self._session = aiohttp.ClientSession(cookies=cookies)

        self._api = EdgeOSWebService(self._host, self._is_ssl, self._session)

        self._ws = EdgeOSWebSocket(self._edgeos_url,
                                   self._edgeos_login_service.session_id,
                                   self._topics, self._session, self.ws_handler)

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

            await self._edgeos_ha.update(interfaces, devices, unknown_devices, system_state,
                                         api_last_update, web_socket_last_update)
        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(f'Failed to refresh data, Error: {ex}, Line: {line_number}')

    def log_edgeos_data(self):
        try:
            path = self._hass.config.path(EDGEOS_DATA_LOG)

            with open(path, 'w+') as out:
                out.write(str(self._edgeos_data))

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(f'Failed to log EdgeOS data, Error: {ex}, Line: {line_number}')

    def ws_handler(self, payload=None):
        try:
            if payload is not None:
                for key in payload:
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

                        host_data[CONNECTED] = TRUE_STR
                        device_data = data.get(host_data_ip, {})

                        for service in device_data:
                            service_data = device_data.get(service, {})
                            for item in service_data:
                                current_value = int(host_data_traffic.get(item, 0))
                                service_data_item_value = int(service_data.get(item, 0))

                                host_data_traffic[item] = current_value + service_data_item_value

                        for traffic_data_item in host_data_traffic:
                            host_data[traffic_data_item] = host_data_traffic.get(traffic_data_item)

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


class EdgeOSHomeAssistant:
    def __init__(self, hass, monitored_interfaces, monitored_devices, unit):
        self._hass = hass
        self._monitored_interfaces = monitored_interfaces
        self._monitored_devices = monitored_devices
        self._unit = unit
        self._unit_size = ALLOWED_UNITS.get(self._unit, BYTE)

    async def update(self, interfaces, devices, unknown_devices, system_state, api_last_update, web_socket_last_update):
        await self.create_interface_sensors(interfaces)
        await self.create_device_sensors(devices)
        await self.create_unknown_devices_sensor(unknown_devices)
        await self.create_system_sensor(system_state, api_last_update, web_socket_last_update)

    async def create_device_sensors(self, devices):
        try:
            for hostname in devices:
                host_data = devices.get(hostname, {})

                await self.create_device_sensor(hostname, host_data)

        except Exception as ex:
            self.log_exception(ex, 'Failed to updated devices')

    async def create_interface_sensors(self, interfaces):
        try:
            for interface in interfaces:
                interface_data = interfaces.get(interface)

                await self.create_interface_sensor(interface, interface_data)

        except Exception as ex:
            error_message = f'Failed to update {INTERFACES_KEY}'

            self.log_exception(ex, error_message)

    async def create_interface_sensor(self, key, data):
        await self.create_sensor(key, data, self._monitored_interfaces,
                                 ENTITY_ID_INTERFACE_BINARY_SENSOR, 'Interface',
                                 LINK_UP, self.get_interface_attributes)

    async def create_device_sensor(self, key, data):
        await self.create_sensor(key, data, self._monitored_devices,
                                 ENTITY_ID_DEVICE_BINARY_SENSOR, 'Device',
                                 CONNECTED, self.get_device_attributes)

    async def create_sensor(self, key, data, allowed_items, entity_id_template, sensor_type,
                            main_attribute, get_attributes):
        try:
            if key in allowed_items:
                entity_id = entity_id_template.format(slugify(key))
                main_entity_details = data.get(main_attribute, FALSE_STR)

                device_attributes = {
                    ATTR_DEVICE_CLASS: DEVICE_CLASS_CONNECTIVITY,
                    ATTR_FRIENDLY_NAME: f'EdgeOS {sensor_type} {key}'
                }

                for data_item_key in data:
                    if data_item_key != main_attribute:
                        value = data.get(data_item_key)
                        attr = get_attributes(data_item_key)

                        name = attr.get(ATTR_NAME, data_item_key)
                        unit_of_measurement = attr.get(ATTR_UNIT_OF_MEASUREMENT)

                        if unit_of_measurement is None:
                            device_attributes[name] = value
                        else:
                            name = name.format(self._unit)

                            device_attributes[name] = (int(value) * BITS_IN_BYTE) / self._unit_size

                if str(main_entity_details).lower() == TRUE_STR:
                    state = STATE_ON
                else:
                    state = STATE_OFF

                current_entity = self._hass.states.get(entity_id)

                device_attributes[EVENT_TIME_CHANGED] = datetime.now().strftime(DEFAULT_DATE_FORMAT)

                if current_entity is not None and current_entity.state == state:
                    entity_attributes = current_entity.attributes
                    device_attributes[EVENT_TIME_CHANGED] = entity_attributes.get(EVENT_TIME_CHANGED)

                self._hass.states.async_set(entity_id, state, device_attributes)

        except Exception as ex:
            error_message = f'Failed to create {key} sensor {sensor_type} with the following data: {data}'

            self.log_exception(ex, error_message)

    async def create_unknown_devices_sensor(self, unknown_devices):
        try:
            devices_count = len(unknown_devices)

            entity_id = ENTITY_ID_UNKNOWN_DEVICES
            state = devices_count

            attributes = {}

            if devices_count > 0:
                attributes[STATE_UNKNOWN] = unknown_devices

            self._hass.states.async_set(entity_id, state, attributes)
        except Exception as ex:
            error_message = f'Failed to create unknown device sensor, Data: {unknown_devices}'

            self.log_exception(ex, error_message)

    async def create_system_sensor(self, system_state, api_last_update, web_socket_last_update):
        try:
            if system_state is not None:
                attributes = {
                    ATTR_UNIT_OF_MEASUREMENT: 'seconds',
                    ATTR_FRIENDLY_NAME: 'EdgeOS System Uptime',
                    ATTR_API_LAST_UPDATE: api_last_update,
                    ATTR_WEBSOCKET_LAST_UPDATE: web_socket_last_update
                }

                for key in system_state:
                    if key != UPTIME:
                        attributes[key] = system_state[key]

                entity_id = 'sensor.edgeos_system_uptime'
                state = system_state.get(UPTIME, 0)

                self._hass.states.async_set(entity_id, state, attributes)
        except Exception as ex:
            error_message = 'Failed to create system sensor'

            self.log_exception(ex, error_message)

    @staticmethod
    def get_device_attributes(key):
        result = DEVICE_SERVICES_STATS_MAP.get(key, {})

        return result

    @staticmethod
    def get_interface_attributes(key):
        all_attributes = {**INTERFACES_MAIN_MAP, **INTERFACES_STATS_MAP}

        result = all_attributes.get(key, {})

        return result

    @staticmethod
    def log_exception(ex, message):
        exc_type, exc_obj, tb = sys.exc_info()
        line_number = tb.tb_lineno

        _LOGGER.error(f'{message}, Error: {ex}, Line: {line_number}')


class EdgeOSWebLogin(requests.Session):
    def __init__(self, host, is_ssl, username, password):
        requests.Session.__init__(self)

        self._credentials = {
            CONF_USERNAME: username,
            CONF_PASSWORD: password
        }

        self._is_ssl = is_ssl

        protocol = PROTOCOL_UNSECURED
        if self._is_ssl:
            protocol = PROTOCOL_SECURED

        self._last_valid = EMPTY_LAST_VALID
        self._edgeos_url = API_URL_TEMPLATE.format(protocol, host)

        ''' This function turns off InsecureRequestWarnings '''
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    @property
    def session_id(self):
        session_id = None

        if self.cookies is not None and COOKIE_PHPSESSID in self.cookies:
            session_id = self.cookies[COOKIE_PHPSESSID]

        return session_id

    @property
    def cookies_data(self):
        return self.cookies

    def login(self):
        try:
            if self._is_ssl:
                login_response = self.post(self._edgeos_url, data=self._credentials, verify=False)
            else:
                login_response = self.post(self._edgeos_url, data=self._credentials)

            login_response.raise_for_status()

            _LOGGER.debug("Sleeping 2 to make sure the session id is in the filesystem")
            sleep(2)

            return True
        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(f'Failed to login, Error: {ex}, Line: {line_number}')

        return False


class EdgeOSWebService:
    def __init__(self, host, is_ssl, session):
        self._last_update = datetime.now()
        self._session = session
        self._is_ssl = is_ssl

        protocol = PROTOCOL_UNSECURED
        if self._is_ssl:
            protocol = PROTOCOL_SECURED

        self._last_valid = EMPTY_LAST_VALID
        self._edgeos_url = API_URL_TEMPLATE.format(protocol, host)

    async def async_get(self, url):
        async with self._session.get(url, ssl=False) as response:
            response.raise_for_status()

            result = await response.json()

            self._last_update = datetime.now()

            return result

    @property
    def last_update(self):
        result = self._last_update

        return result

    async def heartbeat(self, max_age=HEARTBEAT_MAX_AGE):
        try:
            ts = datetime.now()
            current_invocation = datetime.now() - self._last_valid
            if current_invocation > timedelta(seconds=max_age):
                current_ts = str(int(ts.timestamp()))

                heartbeat_req_url = self.get_edgeos_api_endpoint(EDGEOS_API_HEARTBREAT)
                heartbeat_req_full_url = API_URL_HEARTBEAT_TEMPLATE.format(heartbeat_req_url, current_ts)

                response = await self.async_get(heartbeat_req_full_url)

                _LOGGER.debug(f'Heartbeat response: {response}')

                self._last_valid = ts
        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(f'Failed to perform heartbeat, Error: {ex}, Line: {line_number}')

    async def get_devices_data(self):
        result = None

        try:
            get_req_url = self.get_edgeos_api_endpoint(EDGEOS_API_GET)

            result_json = await self.async_get(get_req_url)

            if RESPONSE_SUCCESS_KEY in result_json:
                success_key = str(result_json.get(RESPONSE_SUCCESS_KEY, '')).lower()

                if success_key == TRUE_STR:
                    if EDGEOS_API_GET.upper() in result_json:
                        result = result_json.get(EDGEOS_API_GET.upper(), {})
                else:
                    error_message = result_json[RESPONSE_ERROR_KEY]
                    _LOGGER.error(f'Failed, Error: {error_message}')
            else:
                _LOGGER.error('Invalid response, not contain success status')

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(f'Failed to get devices data, Error: {ex}, Line: {line_number}')

        return result

    async def get_general_data(self, item):
        try:
            data_req_url = self.get_edgeos_api_endpoint(EDGEOS_API_DATA)
            data_req_full_url = API_URL_DATA_TEMPLATE.format(data_req_url, item.replace('-', '_'))

            data = await self.async_get(data_req_full_url)

            if str(data.get(RESPONSE_SUCCESS_KEY, '')) == RESPONSE_FAILURE_CODE:
                error = data.get(RESPONSE_ERROR_KEY, '')

                _LOGGER.error(f'Failed to load {item}, Reason: {error}')
                result = None
            else:
                result = data.get(RESPONSE_OUTPUT)
        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(f'Failed to load {item}, Error: {ex}, Line: {line_number}')
            result = None

        return result

    def get_edgeos_api_endpoint(self, controller):
        url = EDGEOS_API_URL.format(self._edgeos_url, controller)

        return url

    @staticmethod
    def get_device_attributes(key):
        result = DEVICE_SERVICES_STATS_MAP.get(key, {})

        return result

    @staticmethod
    def get_interface_attributes(key):
        all_attributes = {**INTERFACES_MAIN_MAP, **INTERFACES_STATS_MAP}

        result = all_attributes.get(key, {})

        return result


# noinspection PyCompatibility
class EdgeOSWebSocket:

    def __init__(self, edgeos_url, session_id, topics, session, edgeos_callback):
        self._last_update = datetime.now()
        self._edgeos_url = edgeos_url
        self._edgeos_callback = edgeos_callback
        self._session_id = session_id
        self._topics = topics
        self._session = session

        self._stopping = False
        self._pending_payloads = []

        self._timeout = SCAN_INTERVAL.seconds

    @property
    def last_update(self):
        result = self._last_update

        return result

    def parse_message(self, message):
        parsed = False

        try:
            message = message.replace('\n', '')
            message = re.sub('^([0-9]{1,5})', '', message)

            if len(self._pending_payloads) > 0:
                message_previous = ''.join(self._pending_payloads)
                message = f'{message_previous}{message}'

            if len(message) > 0:
                payload_json = json.loads(message)

                self._edgeos_callback(payload_json)
                parsed = True
            else:
                _LOGGER.debug(f'parse_message - Skipping message (Empty)')

        except Exception as ex:
            _LOGGER.debug(f'parse_message - Cannot parse partial payload, Error: {ex}')

        finally:
            if parsed or len(self._pending_payloads) > 3:
                self._pending_payloads = []
            else:
                self._pending_payloads.append(message)

    async def initialize(self):
        _LOGGER.info('initialize - Initialize connection')
        self._stopping = False

        url = urlparse(self._edgeos_url)
        ws_url = WEBSOCKET_URL_TEMPLATE.format(url.netloc)

        subscription_data = self.get_subscription_data()

        async with self._session.ws_connect(ws_url,
                                            origin=self._edgeos_url,
                                            ssl=False,
                                            max_msg_size=0,
                                            timeout=self._timeout) as ws:
            _LOGGER.info(f'Connection connected, Subscribing to: {subscription_data}')

            await ws.send_str(subscription_data)

            _LOGGER.info('Subscribed')

            async for msg in ws:
                if self._stopping:
                    _LOGGER.info("Connection closed (By Home Assistant)")
                    break

                if msg.type == aiohttp.WSMsgType.CLOSED:
                    _LOGGER.info("Connection closed (By Message Close)")
                    break

                elif msg.type == aiohttp.WSMsgType.ERROR:
                    _LOGGER.warning(f'Connection error, Description: {ws.exception()}')
                    break

                else:
                    self._last_update = datetime.now()

                    self.parse_message(msg.data)

            _LOGGER.info(f'Closing connection')

            await ws.close()

            _LOGGER.info(f'Connection closed')

    def stop(self):
        self._stopping = True

    def get_subscription_data(self):
        topics_to_subscribe = [{WS_TOPIC_NAME: topic} for topic in self._topics]
        topics_to_unsubscribe = []

        data = {
            WS_TOPIC_SUBSCRIBE: topics_to_subscribe,
            WS_TOPIC_UNSUBSCRIBE: topics_to_unsubscribe,
            WS_SESSION_ID: self._session_id
        }

        subscription_content = json.dumps(data, separators=(',', ':'))
        subscription_content_length = len(subscription_content)
        subscription_data = f'{subscription_content_length}\n{subscription_content}'

        _LOGGER.info(f'get_subscription_data - Subscription data: {subscription_data}')

        return subscription_data
