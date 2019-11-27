"""Constants for the cloud component."""
from datetime import datetime, timedelta
from homeassistant.const import (ATTR_NAME, ATTR_UNIT_OF_MEASUREMENT)

VERSION = '1.0.7'

DOMAIN = 'edgeos'
DATA_EDGEOS = 'edgeos_data'
SIGNAL_UPDATE_EDGEOS = "edgeos_update"
DEFAULT_NAME = 'EdgeOS'

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

DISCONNECTED_INTERVAL = 60

TRUE_STR = 'true'
FALSE_STR = 'false'

LINK_UP = 'up'

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
IS_ALIVE = 'is_alive'

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
CONNECTED = 'Connected'
LAST_ACTIVITY = 'Last Activity'

DEFAULT_USERNAME = 'ubnt'

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
WS_PAYLOAD_EXCEPTION = 'exception'

SSL_OPTIONS_CERT_REQS = 'cert_reqs'
SSL_OPTIONS_SSL_VERSION = 'ssl_version'
SSL_OPTIONS_CA_CERTS = 'ca_certs'

ARG_SSL_OPTIONS = 'sslopt'
ARG_ORIGIN = 'origin'

ENTITY_ID_UNKNOWN_DEVICES = 'sensor.edgeos_unknown_devices'

ATTR_LAST_CHANGED = "Last Changed"
ATTR_WEB_SOCKET_LAST_UPDATE = 'WS Last Update'
ATTR_API_LAST_UPDATE = 'API Last Update'
ATTR_DEVICE_CLASS = 'device_class'
ATTR_UNKNOWN_DEVICES = "Unknown Devices"
DEVICE_CLASS_CONNECTIVITY = 'connectivity'

DEFAULT_DATE_FORMAT = '%x %X'

EDGEOS_DATA_LOG = 'edgeos_data.log'

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

SCAN_INTERVAL = timedelta(seconds=60)
EMPTY_LAST_VALID = datetime.fromtimestamp(100000)

MAX_MSG_SIZE = 0
MAX_PENDING_PAYLOADS = 3

EMPTY_STRING = ''
NEW_LINE = '\n'
BEGINS_WITH_SIX_DIGITS = '^([0-9]{1,6})'

SENSOR_TYPE_INTERFACE = 'Interface'
SENSOR_TYPE_DEVICE = 'Device'

ATTR_SECONDS = 'seconds'
ATTR_SYSTEM_UPTIME = 'System Uptime'
ATTR_SYSTEM_STATUS = 'System Status'

STRING_DASH = '-'
STRING_UNDERSCORE = '_'
STRING_COMMA = ','
STRING_COLON = ':'

CONF_SUPPORTED_DEVICES = 'supported_devices'
ATTR_ENABLED = 'enabled'

ERROR_SHUTDOWN = "Connector is closed."
