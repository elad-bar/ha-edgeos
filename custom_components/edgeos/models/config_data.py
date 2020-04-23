from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PASSWORD, CONF_USERNAME

from ..helpers.const import *


class ConfigData:
    name: str
    host: str
    port: int
    username: str
    password: str
    password_clear_text: str
    unit: int
    update_interval: int
    monitored_devices: list
    monitored_interfaces: list
    device_trackers: list

    def __init__(self):
        self.name = ""
        self.host = ""
        self.port = 0
        self.username = ""
        self.password = ""
        self.password_clear_text = ""
        self.unit = ATTR_BYTE
        self.update_interval = 1
        self.monitored_devices = []
        self.monitored_interfaces = []
        self.device_trackers = []

    @property
    def unit_size(self):
        return ALLOWED_UNITS[self.unit]

    @property
    def has_credentials(self):
        has_username = self.username and len(self.username) > 0
        has_password = self.password_clear_text and len(self.password_clear_text) > 0

        has_credentials = has_username or has_password

        return has_credentials

    def __repr__(self):
        obj = {
            CONF_NAME: self.name,
            CONF_HOST: self.host,
            CONF_USERNAME: self.username,
            CONF_PASSWORD: self.password,
            CONF_UNIT: self.unit,
            CONF_UPDATE_INTERVAL: self.update_interval,
            CONF_MONITORED_DEVICES: self.monitored_devices,
            CONF_MONITORED_INTERFACES: self.monitored_interfaces,
            CONF_TRACK_DEVICES: self.device_trackers,
        }

        to_string = f"{obj}"

        return to_string
