"""
Following constants are mandatory for CORE:
    DEFAULT_NAME - Full name for the title of the integration
    DOMAIN - name of component, will be used as component's domain
    SUPPORTED_PLATFORMS - list of supported HA components to initialize
"""

from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PASSWORD, CONF_USERNAME

DOMAIN = "edgeos"
DEFAULT_NAME = "EdgeOS"
MANUFACTURER = "Ubiquiti"

DATA_KEYS = [
    CONF_HOST,
    CONF_USERNAME,
    CONF_PASSWORD
]

MAXIMUM_RECONNECT = 3

API_URL_TEMPLATE = "https://{}"
WEBSOCKET_URL_TEMPLATE = "wss://{}/ws/stats"

COOKIE_PHPSESSID = "PHPSESSID"
COOKIE_BEAKER_SESSION_ID = "beaker.session.id"
COOKIE_CSRF_TOKEN = "X-CSRF-TOKEN"

HEADER_CSRF_TOKEN = "X-Csrf-token"
