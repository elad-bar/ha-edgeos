import logging
from typing import Optional

from homeassistant.config_entries import ConfigEntry

from ..helpers.const import *

from ..clients.web_api import EdgeOSWebAPI
from ..clients.web_login import EdgeOSWebLogin, LoginException

from ..managers.configuration_manager import ConfigManager
from ..managers.password_manager import PasswordManager
from ..models.config_data import ConfigData

_LOGGER = logging.getLogger(__name__)


class ConfigFlowManager:
    config_manager: ConfigManager
    password_manager: PasswordManager
    options: Optional[dict]
    data: Optional[dict]
    config_entry: ConfigEntry

    def __init__(self, config_entry: Optional[ConfigEntry] = None):
        self.config_entry = config_entry

        self.options = None
        self.data = None
        self._pre_config = False

        if config_entry is not None:
            self._pre_config = True

            self.update_data(self.config_entry.data)
            self.update_options(self.config_entry.options)

        self._is_initialized = True
        self._auth_error = False
        self._hass = None

    def initialize(self, hass):
        self._hass = hass

        if not self._pre_config:
            self.options = {}
            self.data = {}

        self.password_manager = PasswordManager(self._hass)
        self.config_manager = ConfigManager(self.password_manager)

        self._update_entry()

    @property
    def config_data(self) -> ConfigData:
        return self.config_manager.data

    @staticmethod
    def get_user_input_option(options, key):
        result = options.get(key, [OPTION_EMPTY])

        if OPTION_EMPTY in result:
            result.clear()

        return result

    def update_options(self, options: dict, update_entry: bool = False):
        if options is not None:
            new_options = {}

            options_keys = [CONF_MONITORED_DEVICES, CONF_MONITORED_INTERFACES, CONF_TRACK_DEVICES]
            for key in options_keys:
                new_options[key] = self.get_user_input_option(options, key)

            new_options[CONF_UPDATE_INTERVAL] = options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)

            self.options = new_options
        else:
            self.options = {}

        if update_entry:
            self._update_entry()

    def update_data(self, data: dict, update_entry: bool = False):
        new_data = None

        if data is not None:
            new_data = {}
            for key in data:
                new_data[key] = data[key]

        self.data = new_data

        if update_entry:
            self._update_entry()

    def _update_entry(self):
        entry = ConfigEntry(0, "", "", self.data, "", "", {}, options=self.options)

        self.config_manager.update(entry)

    async def edgeos_disconnection_handler(self):
        self._auth_error = True

    async def validate_login(self):
        errors = None
        config_data = self.config_manager.data

        name = config_data.name
        host = config_data.host
        username = config_data.username
        password = config_data.password_clear_text

        try:
            login_api = EdgeOSWebLogin(host, username, password)

            if login_api.login(throw_exception=True):
                edgeos_url = API_URL_TEMPLATE.format(host)
                api = EdgeOSWebAPI(self._hass, edgeos_url, self.edgeos_disconnection_handler)
                cookies = login_api.cookies_data

                await api.initialize(cookies)

                await api.heartbeat()

                if not api.is_connected:
                    _LOGGER.warning(f"Failed to login EdgeOS ({name}) due to invalid credentials")
                    errors = {
                        "base": "invalid_credentials"
                    }

                device_data = await api.get_devices_data()

                if device_data is None:
                    _LOGGER.warning(f"Failed to retrieve EdgeOS ({name}) device data")
                    errors = {
                        "base": "empty_device_data"
                    }
                else:
                    system_data = device_data.get("system", {})
                    traffic_analysis_data = system_data.get("traffic-analysis", {})
                    dpi = traffic_analysis_data.get("dpi", "disable")
                    export = traffic_analysis_data.get("export", "disable")

                    error_prefix = f"Invalid EdgeOS ({name}) configuration -"

                    if dpi != "enable":
                        _LOGGER.warning(f"{error_prefix} Deep Packet Inspection (DPI) is disabled")
                        errors = {
                            "base": "invalid_dpi_configuration"
                        }

                    if export != "enable":
                        _LOGGER.warning(f"{error_prefix} Traffic Analysis Export is disabled")
                        errors = {
                            "base": "invalid_export_configuration"
                        }

            else:
                _LOGGER.warning(f"Failed to login EdgeOS ({name})")

                errors = {
                    "base": "auth_general_error"
                }

        except LoginException as ex:
            _LOGGER.warning(f"Failed to login EdgeOS ({name}) due to HTTP Status Code: {ex.status_code}")

            errors = {
                "base": HTTP_ERRORS.get(ex.status_code, "auth_general_error")
            }

        except Exception as ex:
            _LOGGER.warning(f"Failed to login EdgeOS ({name}) due to general error: {str(ex)}")

            errors = {
                "base": "auth_general_error"
            }

        return errors
