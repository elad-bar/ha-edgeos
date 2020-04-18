"""Config flow to configure HPPrinter."""
import logging

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback, HomeAssistant

from . import get_ha
from .helpers.const import *

from .clients.web_api import EdgeOSWebAPI
from .clients.web_login import EdgeOSWebLogin, LoginException

from .managers.home_assistant import EdgeOSHomeAssistant
from .managers.configuration_manager import ConfigManager
from .managers.password_manager import PasswordManager

_LOGGER = logging.getLogger(__name__)


class EdgeOSConfigFlow:
    config_manager: ConfigManager
    password_manager: PasswordManager
    is_initialized: bool = False
    auth_error: bool
    ha: HomeAssistant
    options: dict
    data: dict

    def initialize(self, hass: HomeAssistant):
        if not self.is_initialized:
            self.password_manager = PasswordManager(hass)
            self.config_manager = ConfigManager(self.password_manager)

            self.is_initialized = True
            self.auth_error = False
            self.ha = hass
            self.options = {}
            self.data = {}

    def get_user_input_option(self, key):
        options = self.options.get(key, [OPTION_EMPTY])

        if OPTION_EMPTY in options:
            options.clear()

        return options

    def update_config_data(self, data: dict, options: dict = None):
        self.data = data
        self.options = options

        if self.options is not None:
            options_keys = [CONF_MONITORED_DEVICES, CONF_MONITORED_INTERFACES, CONF_TRACK_DEVICES]
            for key in options_keys:
                self.options[key] = self.get_user_input_option(key)

        entry = ConfigEntry(0, "", "", data, "", "", {}, options=options)

        self.config_manager.update(entry)

    async def edgeos_disconnection_handler(self):
        self.auth_error = True

    async def validate_login(self):
        errors = None
        config_data = self.config_manager.data

        name = config_data.name
        host = config_data.host
        username = config_data.username
        password = config_data.password

        try:
            login_api = EdgeOSWebLogin(host, username, password)

            if login_api.login(throw_exception=True):
                edgeos_url = API_URL_TEMPLATE.format(host)
                api = EdgeOSWebAPI(self.ha, edgeos_url, self.edgeos_disconnection_handler)
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


@config_entries.HANDLERS.register(DOMAIN)
class EdgeOSFlowHandler(config_entries.ConfigFlow, EdgeOSConfigFlow):
    """Handle a EdgeOS config flow."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return EdgeOSOptionsFlowHandler(config_entry)

    async def async_step_user(self, user_input=None):
        """Handle a flow start."""
        _LOGGER.debug(f"Starting async_step_user of {DEFAULT_NAME}")
        fields = {
            vol.Required(CONF_NAME, DEFAULT_NAME): str,
            vol.Required(CONF_HOST): str,
            vol.Required(CONF_USERNAME): str,
            vol.Required(CONF_PASSWORD): str,
            vol.Optional(CONF_UNIT, default=ATTR_BYTE): vol.In(ALLOWED_UNITS_LIST)
        }

        errors = None

        self.initialize(self.hass)

        if user_input is not None:
            if CONF_PASSWORD is user_input:
                password = user_input[CONF_PASSWORD]
                user_input[CONF_PASSWORD] = self.password_manager.encrypt(password)

            self.update_config_data(user_input)
            errors = await self.validate_login()

            if errors is None:
                return self.async_create_entry(
                    title=self.config_manager.data.name,
                    data=user_input,
                )

        return self.async_show_form(step_id="user", data_schema=vol.Schema(fields), errors=errors)

    async def async_step_import(self, info):
        """Import existing configuration from Z-Wave."""
        _LOGGER.debug(f"Starting async_step_import of {DEFAULT_NAME}")

        return self.async_create_entry(
            title=f"{DEFAULT_NAME} (import from configuration.yaml)",
            data=info,
        )


class EdgeOSOptionsFlowHandler(config_entries.OptionsFlow, EdgeOSConfigFlow):
    """Handle Plex options."""

    def __init__(self, config_entry: ConfigEntry):
        """Initialize EdgeOS options flow."""

        for key in config_entry.options.keys():
            self.options[key] = config_entry.options[key]

        for key in config_entry.data.keys():
            self.data[key] = config_entry.data[key]

    async def async_step_init(self, user_input=None):
        """Manage the EdgeOS options."""
        return await self.async_step_edge_os_additional_settings(user_input)

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

        available_items = {
            OPTION_EMPTY: OPTION_EMPTY
        }

        for item_key in all_items:
            item = all_items[item_key]
            item_name = item.get(CONF_NAME)

            available_items[item_key] = item_name

        return available_items

    async def async_step_edge_os_additional_settings(self, user_input=None):
        _LOGGER.info(f"async_step_edge_os_additional_settings: {user_input}")

        self.initialize(self.hass)

        if user_input is not None:
            self.update_config_data(self.data, user_input)

            return self.async_create_entry(title="", data=self.options)

        config_data = self.config_manager.data
        name = config_data.name

        ha: EdgeOSHomeAssistant = get_ha(self.hass, name)
        system_data = ha.data_manager.system_data

        all_interfaces = self.get_available_options(system_data, INTERFACES_KEY)
        all_devices = self.get_available_options(system_data, STATIC_DEVICES_KEY)

        monitored_devices = self.get_options(config_data.monitored_devices)
        monitored_interfaces = self.get_options(config_data.monitored_interfaces)
        device_trackers = self.get_options(config_data.device_trackers)

        schema = vol.Schema(
            {
                vol.Optional(CONF_MONITORED_DEVICES, default=monitored_devices):
                    cv.multi_select(all_devices),
                vol.Optional(CONF_MONITORED_INTERFACES, default=monitored_interfaces):
                    cv.multi_select(all_interfaces),
                vol.Optional(CONF_TRACK_DEVICES, default=device_trackers):
                    cv.multi_select(all_devices),
                vol.Optional(CONF_UPDATE_INTERVAL, default=config_data.update_interval):
                    cv.positive_int()
            }
        )

        return self.async_show_form(
            step_id="edge_os_additional_settings",
            data_schema=schema,
            description_placeholders=self.data
        )
