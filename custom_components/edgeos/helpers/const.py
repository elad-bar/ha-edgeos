"""Constants for the cloud component."""
from datetime import datetime, timedelta

import voluptuous as vol

from homeassistant.components.binary_sensor import DOMAIN as DOMAIN_BINARY_SENSOR
from homeassistant.components.device_tracker import DOMAIN as DOMAIN_DEVICE_TRACKER
from homeassistant.components.sensor import DOMAIN as DOMAIN_SENSOR
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

MANUFACTURER = "Ubiquiti"

NOTIFICATION_ID = "edgeos_notification"
NOTIFICATION_TITLE = "EdgeOS Setup"

CLEAR_SUFFIX = "_clear"
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

DROP_DOWNS_CONF = [
    CONF_MONITORED_DEVICES,
    CONF_MONITORED_INTERFACES,
    CONF_TRACK_DEVICES,
]

ENTRY_PRIMARY_KEY = CONF_NAME

CONFIG_FLOW_DATA = "config_flow_data"
CONFIG_FLOW_OPTIONS = "config_flow_options"
CONFIG_FLOW_INIT = "config_flow_init"

API_URL_TEMPLATE = "https://{}"
WEBSOCKET_URL_TEMPLATE = "wss://{}/ws/stats"

EDGEOS_API_URL = "{}/api/edge/{}.json"
EDGEOS_API_GET = "get"
EDGEOS_API_DATA = "data"
EDGEOS_API_HEARTBREAT = "heartbeat"

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

LINK_UP = "up"

INTERFACES_STATS = "stats"

BYTE = 1
KILO_BYTE = BYTE * 1024
MEGA_BYTE = KILO_BYTE * 1024

ATTR_KILO = "KBytes"
ATTR_MEGA = "MBytes"
ATTR_BYTE = "Bytes"

INTERFACES_KEY = "interfaces"
SYSTEM_STATS_KEY = "system-stats"
EXPORT_KEY = "export"
STATIC_DEVICES_KEY = "static-devices"
DHCP_LEASES_KEY = "dhcp-leases"
DHCP_STATS_KEY = "dhcp_stats"
ROUTES_KEY = "routes"
SYS_INFO_KEY = "sys_info"
NUM_ROUTES_KEY = "num-routes"
USERS_KEY = "users"
DISCOVER_KEY = "discover"
UNKNOWN_DEVICES_KEY = "unknown-devices"

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

DEFAULT_USERNAME = "ubnt"

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

ATTR_LAST_CHANGED = "Last Changed"
ATTR_WEB_SOCKET_LAST_UPDATE = "WS Last Update"
ATTR_API_LAST_UPDATE = "API Last Update"
ATTR_DEVICE_CLASS = "device_class"
ATTR_UNKNOWN_DEVICES = "Unknown Devices"
DEVICE_CLASS_CONNECTIVITY = "connectivity"

DEFAULT_DATE_FORMAT = "%x %X"

EDGEOS_DATA_LOG = "edgeos_data.log"

DOMAIN_LOGGER = "logger"
SERVICE_SET_LEVEL = "set_level"

INTERFACES_MAIN_MAP = {
    LINK_UP: {ATTR_NAME: "Connected", ATTR_UNIT_OF_MEASUREMENT: "Connectivity"},
    "speed": {ATTR_NAME: "Link Speed (Mbps)"},
    "duplex": {ATTR_NAME: "Duplex"},
    "mac": {ATTR_NAME: "MAC"},
}

INTERFACES_STATS_MAP = {
    "rx_packets": {ATTR_NAME: "Packets (Received)"},
    "tx_packets": {ATTR_NAME: "Packets (Sent)"},
    "rx_bytes": {ATTR_NAME: "{} (Received)", ATTR_UNIT_OF_MEASUREMENT: "Bytes"},
    "tx_bytes": {ATTR_NAME: "{} (Sent)", ATTR_UNIT_OF_MEASUREMENT: "Bytes"},
    "rx_errors": {ATTR_NAME: "Errors (Received)"},
    "tx_errors": {ATTR_NAME: "Errors (Sent)"},
    "rx_dropped": {ATTR_NAME: "Dropped Packets (Received)"},
    "tx_dropped": {ATTR_NAME: "Dropped Packets (Sent)"},
    "rx_bps": {ATTR_NAME: "{}/ps (Received)", ATTR_UNIT_OF_MEASUREMENT: "Bps"},
    "tx_bps": {ATTR_NAME: "{}/ps (Sent)", ATTR_UNIT_OF_MEASUREMENT: "Bps"},
    "multicast": {ATTR_NAME: "Multicast"},
}

DEVICE_SERVICES_STATS_MAP = {
    "rx_bytes": {ATTR_NAME: "{} (Received)", ATTR_UNIT_OF_MEASUREMENT: "Bytes"},
    "tx_bytes": {ATTR_NAME: "{} (Sent)", ATTR_UNIT_OF_MEASUREMENT: "Bytes"},
    "rx_rate": {ATTR_NAME: "{}/ps (Received)", ATTR_UNIT_OF_MEASUREMENT: "Bps"},
    "tx_rate": {ATTR_NAME: "{}/ps (Sent)", ATTR_UNIT_OF_MEASUREMENT: "Bps"},
}

HEARTBEAT_INTERVAL_SECONDS = 30
HEARTBEAT_INTERVAL = timedelta(seconds=30)
SCAN_INTERVAL_WS_TIMEOUT = timedelta(seconds=60)
SCAN_INTERVAL_API = timedelta(seconds=60)
EMPTY_LAST_VALID = datetime.fromtimestamp(100000)

MAX_MSG_SIZE = 0
MAX_PENDING_PAYLOADS = 3

EMPTY_STRING = ""
NEW_LINE = "\n"
BEGINS_WITH_SIX_DIGITS = "^([0-9]{1,6})"

SENSOR_TYPE_INTERFACE = "Interface"
SENSOR_TYPE_DEVICE = "Device"

ATTR_SECONDS = "seconds"
ATTR_SYSTEM_UPTIME = "System Uptime"
ATTR_SYSTEM_STATUS = "System Status"

STRING_DASH = "-"
STRING_UNDERSCORE = "_"
STRING_COMMA = ","
STRING_COLON = ":"

CONF_SUPPORTED_DEVICES = "supported_devices"
ATTR_ENABLED = "enabled"

ERROR_SHUTDOWN = "Connector is closed."

ENTITY_ICON = "icon"
ENTITY_STATE = "state"
ENTITY_ATTRIBUTES = "attributes"
ENTITY_NAME = "name"
ENTITY_DEVICE_NAME = "device-name"
ENTITY_UNIQUE_ID = "unique-id"
ENTITY_DISABLED = "disabled"

ENTITY_STATUS = "entity-status"
ENTITY_STATUS_EMPTY = None
ENTITY_STATUS_READY = f"{ENTITY_STATUS}-ready"
ENTITY_STATUS_CREATED = f"{ENTITY_STATUS}-created"
ENTITY_STATUS_MODIFIED = f"{ENTITY_STATUS}-modified"
ENTITY_STATUS_IGNORE = f"{ENTITY_STATUS}-ignore"
ENTITY_STATUS_CANCELLED = f"{ENTITY_STATUS}-cancelled"

ICONS = {SENSOR_TYPE_INTERFACE: "mdi:router-network", SENSOR_TYPE_DEVICE: "mdi:devices"}

CONNECTED_ICONS = {True: "mdi:lan-connect", False: "mdi:lan-disconnect"}

SERVICE_LOG_EVENTS_SCHEMA = vol.Schema({vol.Required(ATTR_ENABLED): cv.boolean})

HTTP_ERRORS = {
    404: "not_found",
    403: "invalid_credentials",
    500: "incompatible_version",
}

DOMAIN_LOAD = "load"
DOMAIN_UNLOAD = "unload"

DOMAIN_KEY_FILE = f"{DOMAIN}.key"

CONF_LOG_LEVEL = "log_level"
CONF_LOG_INCOMING_MESSAGES = "log_incoming_messages"

CONF_STORE_DEBUG_FILE = "store_debug_file"

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
