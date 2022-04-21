"""Constants for the cloud component."""
from datetime import datetime, timedelta

import voluptuous as vol

from homeassistant.components.binary_sensor import (
    DOMAIN as DOMAIN_BINARY_SENSOR,
    BinarySensorDeviceClass,
)
from homeassistant.components.device_tracker import DOMAIN as DOMAIN_DEVICE_TRACKER
from homeassistant.components.sensor import (
    DOMAIN as DOMAIN_SENSOR,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.const import (
    ATTR_NAME,
    ATTR_UNIT_OF_MEASUREMENT,
    CONF_HOST,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_USERNAME,
)
from homeassistant.helpers import config_validation as cv

VERSION = "2.0.0"

DOMAIN = "edgeos"
DATA_EDGEOS = "edgeos_data"
DEFAULT_NAME = "EdgeOS"
PASSWORD_MANAGER_EDGEOS = "password_manager_edgeos"
PRODUCT_NAME = f"{DEFAULT_NAME} Device"

SIGNAL_UPDATE_BINARY_SENSOR = f"{DEFAULT_NAME}_{DOMAIN_BINARY_SENSOR}_SIGNLE_UPDATE"
SIGNAL_UPDATE_SENSOR = f"{DEFAULT_NAME}_{DOMAIN_SENSOR}_SIGNLE_UPDATE"
SIGNAL_UPDATE_TRACKERS = f"{DEFAULT_NAME}_{DOMAIN_DEVICE_TRACKER}_SIGNLE_UPDATE"

SIGNALS = {
    DOMAIN_BINARY_SENSOR: SIGNAL_UPDATE_BINARY_SENSOR,
    DOMAIN_SENSOR: SIGNAL_UPDATE_SENSOR,
    DOMAIN_DEVICE_TRACKER: SIGNAL_UPDATE_TRACKERS,
}

EDGEOS_VERSION_INCOMPATIBLE = "v1"
EDGEOS_VERSION_UNKNOWN = "N/A"
EDGEOS_API_URL = "{}/api/edge/{}.json"
EDGEOS_API_GET = "get"
EDGEOS_API_DATA = "data"
EDGEOS_API_HEARTBREAT = "heartbeat"

GENERATE_DEBUG_FILE = "generate_debug_file"

MANUFACTURER = "Ubiquiti"

CLEAR_SUFFIX = "_clear"

ATTR_KILO = "KBytes"
ATTR_MEGA = "MBytes"
ATTR_BYTE = "Bytes"
ATTR_WEB_SOCKET_LAST_UPDATE = "WS Last Update"
ATTR_API_LAST_UPDATE = "API Last Update"
ATTR_UNKNOWN_DEVICES = "Unknown Devices"
ATTR_SYSTEM_STATUS = "System Status"
ATTR_ENABLED = "enabled"

CONF_MONITORED_INTERFACES = "monitored_interfaces"
CONF_MONITORED_INTERFACES_CLEAR = f"{CONF_MONITORED_INTERFACES}{CLEAR_SUFFIX}"
CONF_MONITORED_DEVICES = "monitored_devices"
CONF_MONITORED_DEVICES_CLEAR = f"{CONF_MONITORED_DEVICES}{CLEAR_SUFFIX}"
CONF_TRACK_DEVICES = "track_devices"
CONF_TRACK_DEVICES_CLEAR = f"{CONF_TRACK_DEVICES}{CLEAR_SUFFIX}"
CONF_UNIT = "unit"
CONF_UPDATE_ENTITIES_INTERVAL = "update_entities_interval"
CONF_UPDATE_API_INTERVAL = "update_api_interval"
CONF_CLEAR_CREDENTIALS = "clear-credentials"
CONF_ARR = [CONF_NAME, CONF_HOST, CONF_USERNAME, CONF_PASSWORD, CONF_UNIT]
CONF_LOG_LEVEL = "log_level"
CONF_LOG_INCOMING_MESSAGES = "log_incoming_messages"

ENTRY_PRIMARY_KEY = CONF_NAME

CONFIG_FLOW_DATA = "config_flow_data"
CONFIG_FLOW_OPTIONS = "config_flow_options"
CONFIG_FLOW_INIT = "config_flow_init"

API_URL_TEMPLATE = "https://{}"
WEBSOCKET_URL_TEMPLATE = "wss://{}/ws/stats"



COOKIE_PHPSESSID = "PHPSESSID"
COOKIE_BEAKER_SESSION_ID = "beaker.session.id"

RECONNECT_INTERVAL = 5
DISCONNECT_INTERVAL = 5
DEFAULT_UPDATE_API_INTERVAL = 60
DEFAULT_UPDATE_ENTITIES_INTERVAL = 1

MAXIMUM_RECONNECT = 3
DEFAULT_CONSIDER_AWAY_INTERVAL = 180

CONF_CONSIDER_AWAY_INTERVAL = "consider_away_interval"

TRUE_STR = "true"
FALSE_STR = "false"

LINK_ENABLED = "up"
LINK_CONNECTED = "l1up"

INTERFACES_STATS = "stats"

BYTE = 1
KILO_BYTE = BYTE * 1024
MEGA_BYTE = KILO_BYTE * 1024

INTERFACES_KEY = "interfaces"
SYSTEM_STATS_KEY = "system-stats"
EXPORT_KEY = "export"
STATIC_DEVICES_KEY = "static-devices"
DHCP_STATS_KEY = "dhcp_stats"
SYS_INFO_KEY = "sys_info"
DISCOVER_KEY = "discover"
UNKNOWN_DEVICES_KEY = "unknown-devices"

DHCP_LEASES_KEY = "dhcp-leases"
ROUTES_KEY = "routes"
NUM_ROUTES_KEY = "num-routes"
USERS_KEY = "users"

UPTIME = "uptime"
IS_ALIVE = "is_alive"

DISCOVER_DEVICE_ITEMS = ["hostname", "product", "uptime", "fwversion", "system_status"]

ALLOWED_UNITS = {ATTR_BYTE: BYTE, ATTR_KILO: KILO_BYTE, ATTR_MEGA: MEGA_BYTE}
ALLOWED_UNITS_LIST = [ATTR_BYTE, ATTR_KILO, ATTR_MEGA]

DEVICE_LIST = "devices"
ADDRESS_LIST = "addresses"
ADDRESS_IPV4 = "ipv4"
ADDRESS_HWADDR = "hwaddr"

SERVICE = "service"
DHCP_SERVER = "dhcp-server"
SHARED_NETWORK_NAME = "shared-network-name"
SUBNET = "subnet"
STATIC_MAPPING = "static-mapping"
IP_ADDRESS = "ip-address"
MAC_ADDRESS = "mac-address"
IP = "ip"
MAC = "mac"
CONNECTED = "Connected"
LAST_ACTIVITY = "Last Activity"

RESPONSE_SUCCESS_KEY = "success"
RESPONSE_ERROR_KEY = "error"
RESPONSE_OUTPUT = "output"
RESPONSE_FAILURE_CODE = "0"

HEARTBEAT_MAX_AGE = 15

API_URL_DATA_TEMPLATE = "{}?data={}"
API_URL_HEARTBEAT_TEMPLATE = "{}?t={}"

WS_TOPIC_NAME = "name"
WS_TOPIC_UNSUBSCRIBE = "UNSUBSCRIBE"
WS_TOPIC_SUBSCRIBE = "SUBSCRIBE"
WS_SESSION_ID = "SESSION_ID"

UNIT_PACKETS = "Packets"
UNIT_TRAFFIC = "Traffic"
UNIT_RATE = "Rate"
UNIT_BPS = "bps"
UNIT_BYTES = "bytes"
UNIT_DROPPED_PACKETS = "Dropped"
UNIT_DEVICES = "Devices"

DEFAULT_DATE_FORMAT = "%x %X"

DOMAIN_LOGGER = "logger"
SERVICE_SET_LEVEL = "set_level"

INTERFACES_MAIN_MAP = {
    LINK_CONNECTED: {ATTR_NAME: "Connected", ATTR_UNIT_OF_MEASUREMENT: "Connectivity"},
    LINK_ENABLED: {ATTR_NAME: "Enabled"},
    "speed": {ATTR_NAME: "Link Speed (Mbps)"},
    "duplex": {ATTR_NAME: "Duplex"},
    "mac": {ATTR_NAME: "MAC"},
}

DEVICES_MAIN_MAP = {
    LINK_CONNECTED: {ATTR_NAME: "Connected", ATTR_UNIT_OF_MEASUREMENT: "Connectivity"},
    "ip": {ATTR_NAME: "Address"},
    "mac": {ATTR_NAME: "MAC"},
}

STATS_DIRECTION = {
    "rx": "Received",
    "tx": "Sent"
}

INTERFACES_STATS_MAP = {
    "rx_packets": SensorStateClass.TOTAL_INCREASING,
    "tx_packets": SensorStateClass.TOTAL_INCREASING,
    "rx_bytes": SensorStateClass.TOTAL_INCREASING,
    "tx_bytes": SensorStateClass.TOTAL_INCREASING,
    "rx_errors": SensorStateClass.TOTAL_INCREASING,
    "tx_errors": SensorStateClass.TOTAL_INCREASING,
    "rx_dropped": SensorStateClass.TOTAL_INCREASING,
    "tx_dropped": SensorStateClass.TOTAL_INCREASING,
    "rx_bps": SensorStateClass.MEASUREMENT,
    "tx_bps": SensorStateClass.MEASUREMENT,
    "multicast": SensorStateClass.TOTAL_INCREASING,
}

DEVICE_SERVICES_STATS_MAP = {
    "rx_bytes": SensorStateClass.TOTAL_INCREASING,
    "tx_bytes": SensorStateClass.TOTAL_INCREASING,
    "rx_rate": SensorStateClass.MEASUREMENT,
    "tx_rate": SensorStateClass.MEASUREMENT
}

STATS_MAPS = {
    INTERFACES_KEY: INTERFACES_STATS_MAP,
    STATIC_DEVICES_KEY: DEVICE_SERVICES_STATS_MAP
}

HEARTBEAT_INTERVAL_SECONDS = 30
SCAN_INTERVAL_WS_TIMEOUT = timedelta(seconds=60)
EMPTY_LAST_VALID = datetime.fromtimestamp(100000)

MAX_MSG_SIZE = 0
MAX_PENDING_PAYLOADS = 3

EMPTY_STRING = ""
NEW_LINE = "\n"
BEGINS_WITH_SIX_DIGITS = "^([0-9]{1,6})"

SENSOR_TYPE_INTERFACE = "Interface"
SENSOR_TYPE_DEVICE = "Device"
SENSOR_TYPES = {
    INTERFACES_KEY: SENSOR_TYPE_INTERFACE,
    STATIC_DEVICES_KEY: SENSOR_TYPE_DEVICE
}

STRING_DASH = "-"
STRING_UNDERSCORE = "_"
STRING_COMMA = ","
STRING_COLON = ":"

ERROR_SHUTDOWN = "Connector is closed."

ENTITY_ICON = "icon"
ENTITY_STATE = "state"
ENTITY_ATTRIBUTES = "attributes"
ENTITY_NAME = "name"
ENTITY_DEVICE_NAME = "device-name"
ENTITY_UNIQUE_ID = "unique-id"
ENTITY_DISABLED = "disabled"
ENTITY_BINARY_SENSOR_DEVICE_CLASS = "binary-sensor-device-class"
ENTITY_SENSOR_DEVICE_CLASS = "sensor-device-class"
ENTITY_SENSOR_STATE_CLASS = "sensor-state-class"

ENTITY_STATUS = "entity-status"
ENTITY_STATUS_READY = f"{ENTITY_STATUS}-ready"
ENTITY_STATUS_CREATED = f"{ENTITY_STATUS}-created"

ICONS = {SENSOR_TYPE_INTERFACE: "mdi:router-network", SENSOR_TYPE_DEVICE: "mdi:devices"}

CONNECTED_ICONS = {True: "mdi:lan-connect", False: "mdi:lan-disconnect"}

HTTP_ERRORS = {
    400: "incompatible_version",
    404: "not_found",
    403: "invalid_credentials",
    500: "incompatible_version",
}

DOMAIN_KEY_FILE = f"{DOMAIN}.key"

LOG_LEVEL_DEFAULT = "Default"
LOG_LEVEL_DEBUG = "Debug"
LOG_LEVEL_INFO = "Info"
LOG_LEVEL_WARNING = "Warning"
LOG_LEVEL_ERROR = "Error"

LOG_LEVELS = [
    LOG_LEVEL_DEFAULT,
    LOG_LEVEL_DEBUG,
    LOG_LEVEL_INFO,
    LOG_LEVEL_WARNING,
    LOG_LEVEL_ERROR,
]
