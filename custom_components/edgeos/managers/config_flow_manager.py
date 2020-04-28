import logging
from typing import Optional

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PASSWORD, CONF_USERNAME

from .. import get_ha
from ..clients import LoginException
from ..clients.web_api import EdgeOSWebAPI
from ..helpers.const import *
from ..managers.configuration_manager import ConfigManager
from ..managers.password_manager import PasswordManager
from ..models.config_data import ConfigData
from .home_assistant import EdgeOSHomeAssistant

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

            for key in options:
                new_options[key] = options[key]

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

    @staticmethod
    def get_default_data():
        fields = {
            vol.Required(CONF_NAME, DEFAULT_NAME): str,
            vol.Required(CONF_HOST): str,
            vol.Required(CONF_USERNAME): str,
            vol.Required(CONF_PASSWORD): str,
            vol.Optional(CONF_UNIT, default=ATTR_BYTE): vol.In(ALLOWED_UNITS_LIST),
        }

        data_schema = vol.Schema(fields)

        return data_schema

    def get_default_options(self):
        config_data = self.config_data
        name = config_data.name

        ha: EdgeOSHomeAssistant = get_ha(self._hass, name)
        system_data = ha.data_manager.system_data

        all_interfaces = self.get_available_options(system_data, INTERFACES_KEY)
        all_devices = self.get_available_options(system_data, STATIC_DEVICES_KEY)

        monitored_devices = self.get_options(config_data.monitored_devices)
        monitored_interfaces = self.get_options(config_data.monitored_interfaces)
        device_trackers = self.get_options(config_data.device_trackers)

        data_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_MONITORED_DEVICES, default=monitored_devices
                ): cv.multi_select(all_devices),
                vol.Optional(
                    CONF_MONITORED_INTERFACES, default=monitored_interfaces
                ): cv.multi_select(all_interfaces),
                vol.Optional(
                    CONF_TRACK_DEVICES, default=device_trackers
                ): cv.multi_select(all_devices),
                vol.Optional(
                    CONF_UPDATE_INTERVAL, default=config_data.update_interval
                ): cv.positive_int,
                vol.Optional(CONF_STORE_DEBUG_FILE, default=False): bool,
                vol.Required(CONF_LOG_LEVEL, default=config_data.log_level): vol.In(
                    LOG_LEVELS
                ),
                vol.Optional(
                    CONF_LOG_INCOMING_MESSAGES,
                    default=config_data.log_incoming_messages,
                ): bool,
            }
        )

        return data_schema

    @staticmethod
    def get_options(data):
        result = []

        if data is not None:
            if isinstance(data, list):
                result = data
            else:
                clean_data = data.replace(" ", "")
                result = clean_data.split(",")

        if len(result) == 0:
            result = [OPTION_EMPTY]

        return result

    @staticmethod
    def get_available_options(system_data, key):
        all_items = system_data.get(key)

        available_items = {OPTION_EMPTY: OPTION_EMPTY}

        for item_key in all_items:
            item = all_items[item_key]
            item_name = item.get(CONF_NAME)

            available_items[item_key] = item_name

        return available_items

    async def valid_login(self):
        errors = None
        config_data = self.config_manager.data

        name = config_data.name

        try:
            api = EdgeOSWebAPI(
                self._hass, self.config_manager, self.edgeos_disconnection_handler
            )

            await api.initialize()

            if await api.login(throw_exception=True):
                await api.heartbeat()

                if not api.is_connected:
                    _LOGGER.warning(
                        f"Failed to login EdgeOS ({name}) due to invalid credentials"
                    )
                    errors = {"base": "invalid_credentials"}

                device_data = await api.get_devices_data()

                if device_data is None:
                    _LOGGER.warning(f"Failed to retrieve EdgeOS ({name}) device data")
                    errors = {"base": "empty_device_data"}
                else:
                    system_data = device_data.get("system", {})
                    traffic_analysis_data = system_data.get("traffic-analysis", {})
                    dpi = traffic_analysis_data.get("dpi", "disable")
                    export = traffic_analysis_data.get("export", "disable")

                    error_prefix = f"Invalid EdgeOS ({name}) configuration -"

                    if dpi != "enable":
                        _LOGGER.warning(
                            f"{error_prefix} Deep Packet Inspection (DPI) is disabled"
                        )
                        errors = {"base": "invalid_dpi_configuration"}

                    if export != "enable":
                        _LOGGER.warning(
                            f"{error_prefix} Traffic Analysis Export is disabled"
                        )
                        errors = {"base": "invalid_export_configuration"}

            else:
                _LOGGER.warning(f"Failed to login EdgeOS ({name})")

                errors = {"base": "auth_general_error"}

        except LoginException as ex:
            _LOGGER.warning(
                f"Failed to login EdgeOS ({name}) due to HTTP Status Code: {ex.status_code}"
            )

            errors = {"base": HTTP_ERRORS.get(ex.status_code, "auth_general_error")}

        except Exception as ex:
            _LOGGER.warning(
                f"Failed to login EdgeOS ({name}) due to general error: {str(ex)}"
            )

            errors = {"base": "auth_general_error"}

        return errors
