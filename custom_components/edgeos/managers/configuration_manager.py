from homeassistant.config_entries import ConfigEntry

from ..helpers.const import *
from ..models.config_data import ConfigData
from .password_manager import PasswordManager


class ConfigManager:
    data: ConfigData
    config_entry: ConfigEntry
    password_manager: PasswordManager

    def __init__(self, password_manager: PasswordManager):
        self.password_manager = password_manager

    def set_data(self, data: ConfigData):
        self.data = data

    def update(self, config_entry: ConfigEntry):
        data = config_entry.data
        options = config_entry.options

        result: ConfigData = self.get_basic_data(data)

        result.monitored_devices = options.get(CONF_MONITORED_DEVICES, [])
        result.monitored_interfaces = options.get(CONF_MONITORED_INTERFACES, [])
        result.device_trackers = options.get(CONF_TRACK_DEVICES, [])
        result.update_api_interval = options.get(
            CONF_UPDATE_API_INTERVAL, DEFAULT_UPDATE_API_INTERVAL
        )
        result.update_entities_interval = options.get(
            CONF_UPDATE_ENTITIES_INTERVAL, DEFAULT_UPDATE_ENTITIES_INTERVAL
        )
        result.log_level = options.get(CONF_LOG_LEVEL, LOG_LEVEL_DEFAULT)
        result.log_incoming_messages = options.get(CONF_LOG_INCOMING_MESSAGES, False)
        result.consider_away_interval = options.get(
            CONF_CONSIDER_AWAY_INTERVAL, DEFAULT_CONSIDER_AWAY_INTERVAL
        )

        self.config_entry = config_entry
        self.data = result

    def get_basic_data(self, data):
        result = ConfigData()

        if data is not None:
            result.host = data.get(CONF_HOST)
            result.name = data.get(CONF_NAME, DEFAULT_NAME)
            result.username = data.get(CONF_USERNAME)
            result.password = data.get(CONF_PASSWORD)
            result.unit = data.get(CONF_UNIT, ATTR_BYTE)

            if result.password is not None and len(result.password) > 0:
                result.password_clear_text = self.password_manager.decrypt(
                    result.password
                )
            else:
                result.password_clear_text = result.password

        return result

    @staticmethod
    def _get_config_data_item(key, options, data):
        data_result = data.get(key, "")

        result = options.get(key, data_result)

        return result
