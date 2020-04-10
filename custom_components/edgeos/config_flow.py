"""Config flow to configure HPPrinter."""
import logging

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback

from custom_components.edgeos.web_api import EdgeOSWebAPI
from custom_components.edgeos.web_login import EdgeOSWebLogin, LoginException
from . import EdgeOSHomeAssistant
from .EdgeOSData import EdgeOSData
from .const import *

_LOGGER = logging.getLogger(__name__)


class EdgeOSConfigValidation:
    def __init__(self, hass):
        self._hass = hass
        self._auth_error = False

    async def edgeos_disconnection_handler(self):
        self._auth_error = True

    async def get_login_errors(self, user_input):
        errors = None
        name = user_input.get(CONF_NAME)
        host = user_input.get(CONF_HOST)
        username = user_input.get(CONF_USERNAME)
        password = user_input.get(CONF_PASSWORD)

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
                        _LOGGER.warning(f"{error_prefix} Deep packet investigation (DPI) is disabled")
                        errors = {
                            "base": "invalid_dpi_configuration"
                        }

                    if export != "enable":
                        _LOGGER.warning(f"{error_prefix} Export is disabled")
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
class EdgeOSFlowHandler(config_entries.ConfigFlow):
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

        config_validation = EdgeOSConfigValidation(self.hass)

        fields = {
            vol.Required(CONF_NAME, DEFAULT_NAME): str,
            vol.Required(CONF_HOST): str,
            vol.Required(CONF_USERNAME): str,
            vol.Required(CONF_PASSWORD): str,
            vol.Optional(CONF_UNIT, default=ATTR_BYTE): vol.In(ALLOWED_UNITS_LIST)
        }

        errors = None

        if user_input is not None:
            name = user_input.get(CONF_NAME)
            host = user_input.get(CONF_HOST)
            username = user_input.get(CONF_USERNAME)
            password = user_input.get(CONF_PASSWORD)

            for entry in self._async_current_entries():
                if entry.data[CONF_NAME] == name:
                    _LOGGER.warning(f"EdgeOS ({name}) already configured")

                    return self.async_abort(reason="already_configured",
                                            description_placeholders={
                                                CONF_NAME: name
                                            })

            errors = await config_validation.get_login_errors(user_input)

            if errors is None:
                return self.async_create_entry(
                    title=name,
                    data={
                        CONF_NAME: name,
                        CONF_HOST: host,
                        CONF_USERNAME: username,
                        CONF_PASSWORD: password,
                        CONF_UNIT: user_input.get(CONF_UNIT, ATTR_BYTE)
                    },
                )

        return self.async_show_form(step_id="user", data_schema=vol.Schema(fields), errors=errors)

    async def async_step_import(self, info):
        """Import existing configuration from Z-Wave."""
        _LOGGER.debug(f"Starting async_step_import of {DEFAULT_NAME}")

        return self.async_create_entry(
            title=f"{DEFAULT_NAME} (import from configuration.yaml)",
            data={
                CONF_NAME: info.get(CONF_NAME),
                CONF_HOST: info.get(CONF_HOST),
                CONF_USERNAME: info.get(CONF_USERNAME),
                CONF_PASSWORD: info.get(CONF_PASSWORD),
                CONF_UNIT: info.get(CONF_UNIT)
            },
        )


class EdgeOSOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle Plex options."""

    def __init__(self, config_entry: ConfigEntry):
        """Initialize EdgeOS options flow."""
        self.options = {}
        self._data = {}
        self._config_validation = EdgeOSConfigValidation(self.hass)

        for key in config_entry.options.keys():
            self.options[key] = config_entry.options[key]

        for key in config_entry.data.keys():
            self._data[key] = config_entry.data[key]

    async def async_step_init(self, user_input=None):
        """Manage the EdgeOS options."""
        return await self.async_step_edge_os_additional_settings(user_input)

    def get_option(self, option_key):
        result = []
        data = self.options.get(option_key)

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

    @staticmethod
    def get_user_input_option(user_input, key):
        options = user_input.get(key, [])

        if OPTION_EMPTY in options:
            options = []

        return options

    async def async_step_edge_os_additional_settings(self, user_input=None):
        _LOGGER.info(f"async_step_edge_os_additional_settings: {user_input}")

        if user_input is not None:
            self.options[CONF_MONITORED_DEVICES] = self.get_user_input_option(user_input, CONF_MONITORED_DEVICES)
            self.options[CONF_MONITORED_INTERFACES] = self.get_user_input_option(user_input, CONF_MONITORED_INTERFACES)
            self.options[CONF_TRACK_DEVICES] = self.get_user_input_option(user_input, CONF_TRACK_DEVICES)

            return self.async_create_entry(title="", data=self.options)

        monitored_devices = self.get_option(CONF_MONITORED_DEVICES)
        monitored_interfaces = self.get_option(CONF_MONITORED_INTERFACES)
        track_devices = self.get_option(CONF_TRACK_DEVICES)

        name = self._data.get(CONF_NAME)

        edgeos_data = self.hass.data[DATA_EDGEOS]
        ha: EdgeOSHomeAssistant = edgeos_data.get(name)
        data_manager: EdgeOSData = ha.data_manager
        system_data = data_manager.system_data

        all_interfaces = self.get_available_options(system_data, INTERFACES_KEY)
        all_devices = self.get_available_options(system_data, STATIC_DEVICES_KEY)

        schema = vol.Schema(
            {
                vol.Optional(CONF_MONITORED_DEVICES, default=monitored_devices):
                    cv.multi_select(all_devices),
                vol.Optional(CONF_MONITORED_INTERFACES, default=monitored_interfaces):
                    cv.multi_select(all_interfaces),
                vol.Optional(CONF_TRACK_DEVICES, default=track_devices):
                    cv.multi_select(all_devices),
            }
        )

        return self.async_show_form(
            step_id="edge_os_additional_settings",
            data_schema=schema,
            description_placeholders={
                CONF_NAME: self._data.get(CONF_NAME)
            }
        )
