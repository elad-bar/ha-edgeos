from typing import Optional

from ..helpers.const import *


class ConfigData:
    name: str
    host: str
    port: int
    username: Optional[str]
    password: Optional[str]
    password_clear_text: Optional[str]
    unit: int
    update_entities_interval: int
    update_api_interval: int
    monitored_devices: list
    monitored_interfaces: list
    device_trackers: list
    log_level: str
    log_incoming_messages: bool
    consider_away_interval: int

    def __init__(self):
        self.name = DEFAULT_NAME
        self.host = ""
        self.port = 0
        self.username = None
        self.password = None
        self.password_clear_text = None
        self.unit = ATTR_BYTE
        self.update_entities_interval = DEFAULT_UPDATE_ENTITIES_INTERVAL
        self.update_api_interval = DEFAULT_UPDATE_API_INTERVAL
        self.monitored_devices = []
        self.monitored_interfaces = []
        self.device_trackers = []
        self.log_level = ""
        self.log_incoming_messages = False
        self.store_debug_files = False
        self.consider_away_interval = DEFAULT_CONSIDER_AWAY_INTERVAL

    @property
    def unit_size(self):
        return ALLOWED_UNITS[self.unit]

    @property
    def has_credentials(self):
        has_username = self.username and len(self.username) > 0
        has_password = self.password_clear_text and len(self.password_clear_text) > 0

        has_credentials = has_username or has_password

        return has_credentials

    @property
    def url(self):
        url = API_URL_TEMPLATE.format(self.host)

        return url

    def __repr__(self):
        obj = {
            CONF_NAME: self.name,
            CONF_HOST: self.host,
            CONF_USERNAME: self.username,
            CONF_PASSWORD: self.password,
            CONF_UNIT: self.unit,
            CONF_UPDATE_API_INTERVAL: self.update_api_interval,
            CONF_UPDATE_ENTITIES_INTERVAL: self.update_entities_interval,
            CONF_MONITORED_DEVICES: self.monitored_devices,
            CONF_MONITORED_INTERFACES: self.monitored_interfaces,
            CONF_TRACK_DEVICES: self.device_trackers,
            CONF_LOG_LEVEL: self.log_level,
            CONF_LOG_INCOMING_MESSAGES: self.log_incoming_messages,
            CONF_CONSIDER_AWAY_INTERVAL: self.consider_away_interval,
        }

        to_string = f"{obj}"

        return to_string
