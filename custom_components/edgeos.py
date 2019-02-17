"""
This component provides support for Home Automation Manager (HAM).
For more details about this component, please refer to the documentation at
https://home-assistant.io/components/edgeos/
"""
import sys
import logging
import websocket
import ssl
import requests
from time import sleep
from datetime import datetime, timedelta
import json
from urllib.parse import urlparse
import threading
import urllib3

import voluptuous as vol

from homeassistant.helpers import config_validation as cv
from homeassistant.const import (CONF_SSL, CONF_HOST, CONF_USERNAME, CONF_PASSWORD, EVENT_HOMEASSISTANT_START,
                                 EVENT_HOMEASSISTANT_STOP, STATE_OFF, STATE_ON, ATTR_FRIENDLY_NAME, HTTP_OK,
                                 STATE_UNKNOWN, ATTR_NAME, ATTR_UNIT_OF_MEASUREMENT, EVENT_TIME_CHANGED)

from homeassistant.helpers.event import track_time_interval
from homeassistant.helpers.dispatcher import dispatcher_send
from homeassistant.util import slugify

REQUIREMENTS = ['websocket-client']

DOMAIN = 'edgeos'
DATA_EDGEOS = 'edgeos_data'
SIGNAL_UPDATE_EDGEOS = "edgeos_update"
DEFAULT_NAME = 'EdgeOS'

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=60)

NOTIFICATION_ID = 'edgeos_notification'
NOTIFICATION_TITLE = 'EdgeOS Setup'

CONF_CERT_FILE = 'cert_file'
CONF_MONITORED_INTERFACES = 'monitored_interfaces'
CONF_MONITORED_DEVICES = 'monitored_devices'
CONF_UNIT = 'unit'

API_URL_TEMPLATE = '{}://{}'
WEBSOCKET_URL_TEMPLATE = 'wss://{}/ws/stats'

EDGEOS_API_URL = '{}/api/edge/{}.json'
EDGEOS_API_GET = 'get'
EDGEOS_API_DATA = 'data'
EDGEOS_API_HEARTBREAT = 'heartbeat'

COOKIE_PHPSESSID = 'PHPSESSID'
COOKIE_AS_STR_TEMPLATE = '{}={}'

TRUE_STR = 'true'
FALSE_STR = 'false'

LINK_UP = 'up'

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

INTERFACES_STATS = 'stats'

BITS_IN_BYTE = 8
BYTE = 1
KILO_BYTE = BYTE * 1024
MEGA_BYTE = KILO_BYTE * 1024

ATTR_KILO = 'K'
ATTR_MEGA = 'M'
ATTR_BYTE = ''

INTERFACES_KEY = 'interfaces'
SYSTEM_STATS_KEY = 'system-stats'
EXPORT_KEY = 'export'
STATIC_DEVICES_KEY = 'static-devices'
DHCP_LEASES_KEY = 'dhcp-leases'
DHCP_STATS_KEY = 'dhcp_stats'
ROUTES_KEY = 'routes'
SYS_INFO_KEY = 'sys_info'
NUM_ROUTES_KEY = 'num-routes'
USERS_KEY = 'users'
DISCOVER_KEY = 'discover'
UNKNOWN_DEVICES_KEY = 'unknown-devices'

UPTIME = 'uptime'

SYSTEM_STATS_ITEMS = ['cpu', 'mem', UPTIME]
DISCOVER_DEVICE_ITEMS = ['hostname', 'product', 'uptime', 'fwversion', 'system_status']

ALLOWED_UNITS = {ATTR_BYTE: BYTE, ATTR_KILO: KILO_BYTE, ATTR_MEGA: MEGA_BYTE}

DEVICE_LIST = 'devices'
ADDRESS_LIST = 'addresses'
ADDRESS_IPV4 = 'ipv4'
ADDRESS_HWADDR = 'hwaddr'

SERVICE = 'service'
DHCP_SERVER = 'dhcp-server'
SHARED_NETWORK_NAME = 'shared-network-name'
SUBNET = 'subnet'
STATIC_MAPPING = 'static-mapping'
IP_ADDRESS = 'ip-address'
MAC_ADDRESS = 'mac-address'
IP = 'ip'
MAC = 'mac'
CONNECTED = 'connected'

DEFAULT_USERNAME = 'ubnt'

EMPTY_LAST_VALID = datetime.fromtimestamp(100000)

RESPONSE_SUCCESS_KEY = 'success'
RESPONSE_ERROR_KEY = 'error'
RESPONSE_OUTPUT = 'output'
RESPONSE_FAILURE_CODE = '0'

HEARTBEAT_MAX_AGE = 15

API_URL_DATA_TEMPLATE = '{}?data={}'
API_URL_HEARTBEAT_TEMPLATE = '{}?t={}'

PROTOCOL_UNSECURED = 'http'
PROTOCOL_SECURED = 'https'

WS_TOPIC_NAME = 'name'
WS_TOPIC_UNSUBSCRIBE = 'UNSUBSCRIBE'
WS_TOPIC_SUBSCRIBE = 'SUBSCRIBE'
WS_SESSION_ID = 'SESSION_ID'
WS_PAYLOAD_ERROR = 'payload_error'
WS_PAYLOAD_EXCEPTION = 'exception'

SSL_OPTIONS_CERT_REQS = 'cert_reqs'
SSL_OPTIONS_SSL_VERSION = 'ssl_version'
SSL_OPTIONS_CA_CERTS = 'ca_certs'

ARG_SSL_OPTIONS = 'sslopt'
ARG_ORIGIN = 'origin'

ENTITY_ID_INTERFACE_BINARY_SENSOR = 'binary_sensor.edgeos_interface_{}'
ENTITY_ID_INTERFACE_SENSOR = 'sensor.edgeos_interface_{}_{}'

ENTITY_ID_DEVICE_BINARY_SENSOR = 'binary_sensor.edgeos_device_{}'
ENTITY_ID_DEVICE_SENSOR = 'sensor.edgeos_device_{}_{}'
ENTITY_ID_UNKNOWN_DEVICES = 'sensor.edgeos_unknown_devices'

ATTR_DEVICE_CLASS = 'device_class'
DEVICE_CLASS_CONNECTIVITY = 'connectivity'

DEFAULT_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

EDGEOS_DATA_LOG = 'edgeos_data.log'

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
        cert_file = conf.get(CONF_CERT_FILE, '')
        monitored_interfaces = conf.get(CONF_MONITORED_INTERFACES, [])
        monitored_devices = conf.get(CONF_MONITORED_DEVICES, [])
        unit = conf.get(CONF_UNIT, ATTR_BYTE)
        scan_interval = SCAN_INTERVAL

        data = EdgeOS(hass, host, is_ssl, username, password, cert_file, monitored_interfaces,
                      monitored_devices, unit, scan_interval)

        hass.data[DATA_EDGEOS] = data

        return True
    except Exception as ex:
        exc_type, exc_obj, tb = sys.exc_info()
        line_number = tb.tb_lineno

        _LOGGER.error('Error while initializing EdgeOS, exception: {}, Line: {}'.format(str(ex), line_number))

        hass.components.persistent_notification.create(
            'Error: {}<br />'
            'You will need to restart hass after fixing.'
            ''.format(ex),
            title=NOTIFICATION_TITLE,
            notification_id=NOTIFICATION_ID)

        return False


class EdgeOS(requests.Session):
    def __init__(self, hass, host, is_ssl, username, password, cert_file, monitored_interfaces,
                 monitored_devices, unit, scan_interval):
        requests.Session.__init__(self)

        credentials = {
            CONF_USERNAME: username,
            CONF_PASSWORD: password
        }

        self._scan_interval = scan_interval
        self._hass = hass
        self._cert_file = cert_file
        self._monitored_interfaces = monitored_interfaces
        self._monitored_devices = monitored_devices
        self._is_ssl = is_ssl
        self._unit = unit
        self._unit_size = ALLOWED_UNITS.get(self._unit, BYTE)

        protocol = PROTOCOL_UNSECURED
        if self._is_ssl:
            protocol = PROTOCOL_SECURED

        self._last_valid = EMPTY_LAST_VALID
        self._edgeos_url = API_URL_TEMPLATE.format(protocol, host)

        self._edgeos_data = {}

        self._special_handlers = None
        self._ws_handlers = None
        self._subscribed_topics = []

        self.load_ws_handlers()
        self.load_special_handlers()
        self._ws_connection = None

        ''' This function turns off InsecureRequestWarnings '''
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        def edgeos_initialize(event_time):
            _LOGGER.info('Initialization begun at {}'.format(event_time))
            if self.login(credentials):
                self._ws_connection = EdgeOSWebSocket(self._edgeos_url, self.cookies,
                                                      self._subscribed_topics, self.ws_handler,
                                                      self._cert_file, self._is_ssl)
                self._ws_connection.initialize()

                self.refresh_data()

        def edgeos_stop(event_time):
            _LOGGER.info('Stop begun at {}'.format(event_time))
            if self._ws_connection is not None:
                self._ws_connection.stop()

        def edgeos_restart(event_time):
            _LOGGER.info('Restart begun at {}'.format(event_time))
            if self._ws_connection is not None:
                self._ws_connection.stop()

            self._ws_connection.initialize()

            self.refresh_data()

        def edgeos_refresh(event_time):
            _LOGGER.info('Refresh EdgeOS components ({})'.format(event_time))

            self.refresh_data()

        def edgeos_save_debug_data(event_time):
            _LOGGER.info('Save EdgeOS debug data ({})'.format(event_time))

            self.log_edgeos_data()

        self.i_edgeos_initialize = edgeos_initialize
        self.i_edgeos_stop = edgeos_stop
        self.i_edgeos_restart = edgeos_restart
        self.i_edgeos_refresh = edgeos_refresh
        self.i_edgeos_save_debug_data = edgeos_save_debug_data

        hass.services.register(DOMAIN, 'stop', edgeos_stop)
        hass.services.register(DOMAIN, 'restart', edgeos_restart)
        hass.services.register(DOMAIN, 'save_debug_data', edgeos_save_debug_data)

        track_time_interval(hass, edgeos_refresh, self._scan_interval)

        hass.bus.listen_once(EVENT_HOMEASSISTANT_START, edgeos_initialize)
        hass.bus.listen_once(EVENT_HOMEASSISTANT_STOP, edgeos_stop)

    def refresh_data(self):
        try:
            self.update_edgeos_data()
            self.update_interfaces()
            self.update_devices()
            self.update_unknown_devices()
            self.create_system_sensor()

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error('Failed to refresh data, Error: {}, Line: {}'.format(str(ex), line_number))

    def log_edgeos_data(self):
        try:
            path = self._hass.config.path(EDGEOS_DATA_LOG)

            with open(path, 'w+') as out:
                out.write(str(self._edgeos_data))

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error('Failed to log EdgeOS data, Error: {}, Line: {}'.format(str(ex), line_number))

    def ws_handler(self, payload=None):
        try:
            if payload is not None:
                for key in payload:
                    data = payload.get(key)
                    handler = self._ws_handlers.get(key)

                    if handler is not None:
                        handler(data)
        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error('Failed to handle WS message, Error: {}, Line: {}'.format(str(ex), line_number))

    def heartbeat(self, max_age=HEARTBEAT_MAX_AGE):
        try:
            ts = datetime.now()
            current_invocation = datetime.now() - self._last_valid
            if current_invocation > timedelta(seconds=max_age):
                current_ts = str(int(ts.timestamp()))

                heartbeat_req_url = self.get_edgeos_api_endpoint(EDGEOS_API_HEARTBREAT)
                heartbeat_req_full_url = API_URL_HEARTBEAT_TEMPLATE.format(heartbeat_req_url, current_ts)

                if self._is_ssl:
                    heartbeat_response = self.get(heartbeat_req_full_url, verify=False)
                else:
                    heartbeat_response = self.get(heartbeat_req_full_url)

                heartbeat_response.raise_for_status()

                self._last_valid = ts
        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error('Failed to perform heartbeat, Error: {}, Line: {}'.format(str(ex), line_number))

    def login(self, credentials):
        result = False

        try:
            if self._is_ssl:
                login_response = self.post(self._edgeos_url, data=credentials, verify=False)
            else:
                login_response = self.post(self._edgeos_url, data=credentials)

            login_response.raise_for_status()

            _LOGGER.debug("Sleeping 5 to make sure the session id is in the filesystem")
            sleep(5)

            result = True
        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error('Failed to login due to: {}, Line: {}'.format(str(ex), line_number))

        return result

    def handle_static_devices(self):
        try:
            result = {}

            previous_result = self.get_devices()
            if previous_result is None:
                previous_result = {}

            get_req_url = self.get_edgeos_api_endpoint(EDGEOS_API_GET)

            if self._is_ssl:
                get_result = self.get(get_req_url, verify=False)
            else:
                get_result = self.get(get_req_url)

            if get_result.status_code == HTTP_OK:
                result_json = get_result.json()

                if RESPONSE_SUCCESS_KEY in result_json:
                    success_key = str(result_json.get(RESPONSE_SUCCESS_KEY, '')).lower()

                    if success_key == TRUE_STR:
                        if EDGEOS_API_GET.upper() in result_json:
                            get_data = result_json.get(EDGEOS_API_GET.upper(), {})
                            service_data = get_data.get(SERVICE, {})
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
                    else:
                        _LOGGER.error('Failed, {}'.format(result_json[RESPONSE_ERROR_KEY]))
                else:
                    _LOGGER.error('Invalid response, not contain success status')

            else:
                _LOGGER.error('HTTP Status code returned: {}'.format(get_result.status_code))

            self.update_data(STATIC_DEVICES_KEY, result)
        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error('Failed to load {}, Error: {}, Line: {}'.format(STATIC_DEVICES_KEY, str(ex), line_number))

    def handle_interfaces(self, data):
        try:
            if data is None or data == '':
                return

            result = self.get_edgeos_data(INTERFACES_KEY)

            for interface in data:
                interface_data = None

                if interface in data:
                    interface_data = data.get(interface)

                interface_data_item = self.get_interface_data(interface_data)

                result[interface] = interface_data_item

            self.update_data(INTERFACES_KEY, result)
        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error('Failed to load {}, Error: {}, Line: {}'.format(INTERFACES_KEY, str(ex), line_number))

    def update_devices(self):
        try:
            result = self.get_devices()

            for hostname in result:
                host_data = result.get(hostname, {})

                self.create_device_sensor(hostname, host_data)

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error('Failed to updated devices, Error: {}, Line: {}'.format(str(ex), line_number))

    def update_unknown_devices(self):
        try:
            unknown_devices = self.get_edgeos_data(UNKNOWN_DEVICES_KEY)

            unknown_devices_count = len(unknown_devices)

            self.create_unknown_device_sensor(', '.join(unknown_devices), unknown_devices_count)
        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error('Failed to updated unknown devices, Error: {}, Line: {}'.format(str(ex), line_number))

    def update_interfaces(self):
        try:
            result = self.get_edgeos_data(INTERFACES_KEY)

            for interface in result:
                interface_data = result.get(interface)

                self.create_interface_sensor(interface, interface_data)

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error('Failed to update {}, Error: {}, Line: {}'.format(INTERFACES_KEY, str(ex), line_number))

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
            if data is None or data == '':
                return

            self.update_data(SYSTEM_STATS_KEY, data)
        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error('Failed to load {}, Error: {}, Line: {}'.format(SYSTEM_STATS_KEY, str(ex), line_number))

    def handle_discover(self, data):
        try:
            if data is None or data == '':
                return

            result = self.get_edgeos_data(DISCOVER_KEY)

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

            self.update_data(DISCOVER_KEY, result)
        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error('Failed to load {}, Original Message: {}, Error: {}, Line: {}'.format(DISCOVER_KEY, data,
                                                                                                str(ex), line_number))

    def _data(self, item):
        try:
            data_req_url = self.get_edgeos_api_endpoint(EDGEOS_API_DATA)
            data_req_full_url = API_URL_DATA_TEMPLATE.format(data_req_url, item.replace('-', '_'))

            if self._is_ssl:
                data_response = self.get(data_req_full_url, verify=False)
            else:
                data_response = self.get(data_req_full_url)

            data_response.raise_for_status()

            data = data_response.json()
            if str(data.get(RESPONSE_SUCCESS_KEY, '')) == RESPONSE_FAILURE_CODE:
                error = data.get(RESPONSE_ERROR_KEY, '')

                _LOGGER.error('Failed to load {}, Reason: {}'.format(item, error))
                result = None
            else:
                result = data.get(RESPONSE_OUTPUT)
        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error('Failed to load {}, Error: {}, Line: {}'.format(item, str(ex), line_number))
            result = None

        return result

    def handle_export(self, data):
        try:
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

            self.update_data(STATIC_DEVICES_KEY, result)
            self.update_data(UNKNOWN_DEVICES_KEY, unknown_devices)
        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error('Failed to load {}, Error: {}, Line: {}'.format(EXPORT_KEY, str(ex), line_number))

    @staticmethod
    def handle_payload_error(data):
        _LOGGER.error('Invalid payload received, Payload: {}'.format(data))

    def get_edgeos_data(self, storage):
        data = self._edgeos_data.get(storage, {})

        return data

    def update_edgeos_data(self):
        self.heartbeat()

        handler = self._special_handlers.get(STATIC_DEVICES_KEY)

        if handler is not None:
            handler()

    def update_data(self, storage, data):
        self._edgeos_data[storage] = data

        _LOGGER.debug('Update {}: {}'.format(storage, data))

        dispatcher_send(self._hass, SIGNAL_UPDATE_EDGEOS)

    def load_ws_handlers(self):
        ws_handlers = {
            EXPORT_KEY: self.handle_export,
            INTERFACES_KEY: self.handle_interfaces,
            SYSTEM_STATS_KEY: self.handle_system_stats,
            DISCOVER_KEY: self.handle_discover,
            WS_PAYLOAD_ERROR: self.handle_payload_error
        }

        for handler_name in ws_handlers:
            self._subscribed_topics.append(handler_name)

        self._ws_handlers = ws_handlers

    def load_special_handlers(self):
        special_handlers = {
            STATIC_DEVICES_KEY: self.handle_static_devices
        }

        self._special_handlers = special_handlers

    def get_edgeos_api_endpoint(self, controller):
        url = EDGEOS_API_URL.format(self._edgeos_url, controller)

        return url

    def get_devices(self):
        result = self.get_edgeos_data(STATIC_DEVICES_KEY)

        return result

    def get_device(self, hostname):
        devices = self.get_devices()
        device = devices.get(hostname, {})

        return device

    @staticmethod
    def get_device_name(hostname):
        name = '{} {}'.format(DEFAULT_NAME, hostname)

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

    def create_interface_sensor(self, key, data):
        self.create_sensor(key, data, self._monitored_interfaces,
                           ENTITY_ID_INTERFACE_BINARY_SENSOR, 'Interface',
                           LINK_UP, self.get_interface_attributes)

    def create_device_sensor(self, key, data):
        self.create_sensor(key, data, self._monitored_devices,
                           ENTITY_ID_DEVICE_BINARY_SENSOR, 'Device',
                           CONNECTED, self.get_device_attributes)

    def create_sensor(self, key, data, allowed_items, entity_id_template, sensor_type,
                      main_attribute, get_attributes):
        try:
            if key in allowed_items:
                entity_id = entity_id_template.format(slugify(key))
                main_entity_details = data.get(main_attribute, FALSE_STR)

                device_attributes = {
                    ATTR_DEVICE_CLASS: DEVICE_CLASS_CONNECTIVITY,
                    ATTR_FRIENDLY_NAME: 'EdgeOS {} {}'.format(sensor_type, key)
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

                self._hass.states.set(entity_id, state, device_attributes)

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(
                'Failed to create {} sensor {} with the following data: {}, Error: {}, Line: {}'.format(key,
                                                                                                        sensor_type,
                                                                                                        str(data),
                                                                                                        str(ex),
                                                                                                        line_number))

    def create_unknown_device_sensor(self, devices, devices_count):
        try:
            entity_id = ENTITY_ID_UNKNOWN_DEVICES
            state = devices_count

            attributes = {}

            if devices_count > 0:
                attributes[STATE_UNKNOWN] = devices

            self._hass.states.set(entity_id, state, attributes)
        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(
                'Failed to create unknown device sensor, Data: {}, Error: {}, Line: {}'.format(str(devices),
                                                                                               str(ex),
                                                                                               line_number))

    def create_system_sensor(self):
        try:
            data = self.get_edgeos_data(SYSTEM_STATS_KEY)

            if data is not None:
                attributes = {
                    ATTR_UNIT_OF_MEASUREMENT: 'seconds',
                    ATTR_FRIENDLY_NAME: 'EdgeOS System Uptime'
                }

                for key in data:
                    if key != UPTIME:
                        attributes[key] = data[key]

                entity_id = 'sensor.edgeos_system_uptime'
                state = data.get(UPTIME, 0)

                self._hass.states.set(entity_id, state, attributes)
        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno
            _LOGGER.error(
                'Failed to create system sensor, Error: {}, Line: {}'.format(str(ex), line_number))

    @staticmethod
    def get_device_attributes(key):
        result = DEVICE_SERVICES_STATS_MAP.get(key, {})

        return result

    @staticmethod
    def get_interface_attributes(key):
        all_attributes = {**INTERFACES_MAIN_MAP, **INTERFACES_STATS_MAP}

        result = all_attributes.get(key, {})

        return result


class EdgeOSWebSocket:

    def __init__(self, edgeos_url, cookies, subscribed_topics, consumer_handler, cert_file, is_ssl):
        self._subscribed_topics = subscribed_topics
        self._edgeos_url = edgeos_url
        self._consumer_handler = consumer_handler
        self._cert_file = cert_file
        self._cookies = cookies
        self._is_ssl = is_ssl

        self._delayed_messages = []

        self._subscription_data = None
        self._is_alive = False
        self._session_id = None
        self._ws = None
        self._ws_url = None
        self._thread = None
        self._stopping = False

        self._timeout = SCAN_INTERVAL.seconds

        url = urlparse(self._edgeos_url)
        self._ws_url = WEBSOCKET_URL_TEMPLATE.format(url.netloc)

        self._session_id = self._cookies[COOKIE_PHPSESSID]
        self._cookies_as_str = '; '.join([COOKIE_AS_STR_TEMPLATE.format(*x) for x in self._cookies.items()])

        topics_to_subscribe = [{WS_TOPIC_NAME: x} for x in self._subscribed_topics]
        topics_to_unsubscribe = []

        data = {
            WS_TOPIC_SUBSCRIBE: topics_to_subscribe,
            WS_TOPIC_UNSUBSCRIBE: topics_to_unsubscribe,
            WS_SESSION_ID: self._session_id
        }

        subscription_content = json.dumps(data, separators=(',', ':'))
        subscription_content_length = len(subscription_content)
        subscription_data = "{}\n{}".format(subscription_content_length, subscription_content)

        self._subscription_data = subscription_data

        if self._is_ssl:
            self._ssl_options = {
                SSL_OPTIONS_CERT_REQS: ssl.CERT_NONE,
            }
        else:
            self._ssl_options = {}

        self._consumer_handler()

    def on_message(self, message):
        if self._stopping:
            _LOGGER.warning('Received a message while WS is closed, ignoring message: {}'.format(message))
            return

        payload = None

        try:
            data_arr = message.split('\n')

            content_length_str = data_arr[0]

            if content_length_str.isdigit():
                content_length = int(content_length_str)
                payload_str = message[len(content_length_str) + 1:]

                if content_length == len(payload_str):
                    payload = self.extract_payload(payload_str, message)
                else:
                    self._delayed_messages.append(payload_str)

            elif len(self._delayed_messages) == 1:
                self._delayed_messages.append(message)

                payload_str = ''.join(self._delayed_messages)

                payload = self.extract_payload(payload_str, message, message)

            if payload is None:
                _LOGGER.debug('Payload is empty')
            elif WS_PAYLOAD_ERROR in payload:
                _LOGGER.warning('Unable to parse payload: {}'.format(payload))
            else:
                self._consumer_handler(payload)
        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error('Failed to invoke handler, Payload: {}, Error: {}, Line: {}'.format(payload,
                                                                                              str(ex),
                                                                                              line_number))

    def extract_payload(self, payload_json, original_message, delayed_message=None):
        try:
            result = json.loads(payload_json)
            self._delayed_messages = []
        except Exception as ex:
            if delayed_message is None:
                delayed_message = payload_json

            self._delayed_messages.append(delayed_message)
            result = {
                WS_PAYLOAD_ERROR: original_message,
                WS_PAYLOAD_EXCEPTION: str(ex)
            }

        return result

    def on_error(self, error):
        try:
            if 'Connection is already closed' in str(error):
                self.initialize()
            else:
                _LOGGER.warning('Connection error, Description: {}'.format(error))
        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error('Failed to handle error: {}, Exception: {}, Line: {}'.format(error, str(ex), line_number))

    def on_close(self):
        _LOGGER.info("### closed ###")

        if not self._stopping:
            _LOGGER.info("### restarting ###")

            self.initialize()

    def on_open(self):
        _LOGGER.debug("Subscribing")
        self._ws.send(self._subscription_data)
        _LOGGER.info("Subscribed")

    def initialize(self):
        try:
            if self._ws is not None:
                self.stop()

            self._stopping = False

            self._ws = websocket.WebSocketApp(self._ws_url,
                                              on_message=self.on_message,
                                              on_error=self.on_error,
                                              on_close=self.on_close,
                                              on_open=self.on_open,
                                              cookie=self._cookies_as_str)

            kwargs = {
                ARG_SSL_OPTIONS: self._ssl_options,
                ARG_ORIGIN: self._edgeos_url
            }

            self._thread = threading.Thread(target=self._ws.run_forever, kwargs=kwargs)
            self._thread.daemon = True
            self._thread._running = True
            self._thread.start()

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error('Failed, {}, Line: {}'.format(str(ex), line_number))

    def stop(self):
        try:
            _LOGGER.info("Stopping WebSocket")

            if self._ws is not None:
                self._stopping = True
                self._ws.keep_running = False

            _LOGGER.info("WebSocket Stopped")
        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error('Failed to stop WebSocket, Error: {}, Line: {}'.format(str(ex), line_number))

        try:
            _LOGGER.info("Stopping daemon thread")

            if self._thread is not None:
                self._thread.join()

            _LOGGER.info("Daemon thread stopped")
        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error('Failed to stop daemon thread, Error: {}, Line: {}'.format(str(ex), line_number))
