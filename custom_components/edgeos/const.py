"""Constants for the cloud component."""
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
COOKIE_AS_STR_TEMPLATE = '{}={}'

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

ENTITY_ID_INTERFACE_BINARY_SENSOR = 'binary_sensor.edgeos_interface_{}'
ENTITY_ID_INTERFACE_SENSOR = 'sensor.edgeos_interface_{}_{}'

ENTITY_ID_DEVICE_BINARY_SENSOR = 'binary_sensor.edgeos_device_{}'
ENTITY_ID_DEVICE_SENSOR = 'sensor.edgeos_device_{}_{}'
ENTITY_ID_UNKNOWN_DEVICES = 'sensor.edgeos_unknown_devices'

ATTR_WEBSOCKET_LAST_UPDATE = 'WS Last Update'
ATTR_API_LAST_UPDATE = 'API Last Update'
ATTR_DEVICE_CLASS = 'device_class'
DEVICE_CLASS_CONNECTIVITY = 'connectivity'

DEFAULT_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

EDGEOS_DATA_LOG = 'edgeos_data.log'
