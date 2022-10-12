from homeassistant.components.binary_sensor import DOMAIN as DOMAIN_BINARY_SENSOR
from homeassistant.components.camera import DOMAIN as DOMAIN_CAMERA
from homeassistant.components.device_tracker import DOMAIN as DOMAIN_DEVICE_TRACKER
from homeassistant.components.light import DOMAIN as DOMAIN_LIGHT
from homeassistant.components.media_source import DOMAIN as DOMAIN_MEDIA_SOURCE
from homeassistant.components.select import DOMAIN as DOMAIN_SELECT
from homeassistant.components.sensor import DOMAIN as DOMAIN_SENSOR
from homeassistant.components.stream import DOMAIN as DOMAIN_STREAM
from homeassistant.components.switch import DOMAIN as DOMAIN_SWITCH
from homeassistant.components.vacuum import DOMAIN as DOMAIN_VACUUM

from ...configuration.helpers.const import *

SUPPORTED_PLATFORMS = [
    DOMAIN_BINARY_SENSOR,
    DOMAIN_CAMERA,
    DOMAIN_SELECT,
    DOMAIN_SWITCH,
    DOMAIN_VACUUM,
    DOMAIN_SENSOR,
    DOMAIN_LIGHT,
    DOMAIN_DEVICE_TRACKER
]

PLATFORMS = {domain: f"{DOMAIN}_{domain}_UPDATE_SIGNAL" for domain in SUPPORTED_PLATFORMS}

ENTITY_STATE = "state"
ENTITY_ATTRIBUTES = "attributes"
ENTITY_UNIQUE_ID = "unique-id"
ENTITY_DEVICE_NAME = "device-name"
ENTITY_DETAILS = "details"
ENTITY_DISABLED = "disabled"
ENTITY_DOMAIN = "domain"
ENTITY_STATUS = "status"
ENTITY_CONFIG_ENTRY_ID = "entry_id"

HA_NAME = "homeassistant"
SERVICE_RELOAD = "reload_config_entry"

STORAGE_VERSION = 1

PASSWORD_MANAGER = f"pm_{DOMAIN}"
DATA = f"data_{DOMAIN}"

DOMAIN_KEY_FILE = f"{DOMAIN}.key"

ATTR_OPTIONS = "attr_options"

CONF_STILL_IMAGE_URL = "still_image_url"
CONF_STREAM_SOURCE = "stream_source"
CONF_MOTION_DETECTION = "motion_detection"

ATTR_STREAM_FPS = "stream_fps"
ATTR_MODE_RECORD = "record_mode"
ATTR_FEATURES = "features"
ATTR_FANS_SPEED_LIST = "fan_speed_list"

PROTOCOLS = {True: "https", False: "http"}
WS_PROTOCOLS = {True: "wss", False: "ws"}

ACTION_CORE_ENTITY_RETURN_TO_BASE = "return_to_base"
ACTION_CORE_ENTITY_SET_FAN_SPEED = "set_fan_speed"
ACTION_CORE_ENTITY_START = "start"
ACTION_CORE_ENTITY_STOP = "stop"
ACTION_CORE_ENTITY_PAUSE = "stop"
ACTION_CORE_ENTITY_TURN_ON = "turn_on"
ACTION_CORE_ENTITY_TURN_OFF = "turn_off"
ACTION_CORE_ENTITY_TOGGLE = "toggle"
ACTION_CORE_ENTITY_SEND_COMMAND = "send_command"
ACTION_CORE_ENTITY_LOCATE = "locate"
ACTION_CORE_ENTITY_SELECT_OPTION = "select_option"
ACTION_CORE_ENTITY_ENABLE_MOTION_DETECTION = "enable_motion_detection"
ACTION_CORE_ENTITY_DISABLE_MOTION_DETECTION = "disable_motion_detection"
