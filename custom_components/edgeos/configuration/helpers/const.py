"""
Following constants are mandatory for CORE:
    DEFAULT_NAME - Full name for the title of the integration
    DOMAIN - name of component, will be used as component's domain
    SUPPORTED_PLATFORMS - list of supported HA components to initialize
"""

from homeassistant.const import (
    CONF_HOST,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_PATH,
    CONF_PORT,
    CONF_SSL,
    CONF_USERNAME,
)

DOMAIN = "edgeos"
DEFAULT_NAME = "EdgeOS"
MANUFACTURER = "Ubiquiti"

DEFAULT_PORT = 443

CONFIGURATION_MANAGER = f"cm_{DOMAIN}"

DATA_KEYS = [
    CONF_HOST,
    CONF_PATH,
    CONF_PORT,
    CONF_SSL,
    CONF_USERNAME,
    CONF_PASSWORD
]

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
CONF_LOG_LEVEL = "log_level"
CONF_LOG_INCOMING_MESSAGES = "log_incoming_messages"
CONF_CONSIDER_AWAY_INTERVAL = "consider_away_interval"

RECONNECT_INTERVAL = 5
DISCONNECT_INTERVAL = 5
DEFAULT_UPDATE_API_INTERVAL = 60
DEFAULT_UPDATE_ENTITIES_INTERVAL = 1
MAXIMUM_RECONNECT = 3

API_URL_TEMPLATE = "https://{}"
WEBSOCKET_URL_TEMPLATE = "wss://{}/ws/stats"

COOKIE_PHPSESSID = "PHPSESSID"
COOKIE_BEAKER_SESSION_ID = "beaker.session.id"
COOKIE_CSRF_TOKEN = "X-CSRF-TOKEN"

HEADER_CSRF_TOKEN = "X-Csrf-token"
