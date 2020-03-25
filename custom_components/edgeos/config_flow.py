"""Config flow to configure HPPrinter."""
import logging

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback

from custom_components.edgeos.web_api import EdgeOSWebAPI
from custom_components.edgeos.web_login import EdgeOSWebLogin, LoginException
from .const import *

_LOGGER = logging.getLogger(__name__)


@config_entries.HANDLERS.register(DOMAIN)
class EdgeOSFlowHandler(config_entries.ConfigFlow):
    """Handle a HPPrinter config flow."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL
    _auth_error = False

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return EdgeOSOptionsFlowHandler(config_entry)

    async def edgeos_disconnection_handler(self):
        self._auth_error = True

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

            try:
                login_api = EdgeOSWebLogin(host, username, password)

                if login_api.login(throw_exception=True):
                    edgeos_url = API_URL_TEMPLATE.format(host)
                    api = EdgeOSWebAPI(self.hass, edgeos_url, self.edgeos_disconnection_handler)
                    cookies = login_api.cookies_data

                    await api.initialize(cookies)

                    await api.heartbeat()

                    if not api.is_connected:
                        _LOGGER.warning(f"Failed to login EdgeOS ({name}) due to invalid credentials")
                        errors = {
                            "base": "invalid_credentials"
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

        for key in config_entry.options.keys():
            self.options[key] = config_entry.options[key]

        for key in config_entry.data.keys():
            self._data[key] = config_entry.data[key]

    async def async_step_init(self, user_input=None):
        """Manage the EdgeOS options."""
        return await self.async_step_edge_os_additional_settings(user_input)

    @staticmethod
    def _get_user_input(user_input, key):
        data = user_input.get(key).replace(" ", "")
        clear = user_input.get(f"{key}{CLEAR_SUFFIX}", False)
        if clear:
            data = ""

        return data

    async def async_step_edge_os_additional_settings(self, user_input=None):
        fields_items = [CONF_MONITORED_DEVICES, CONF_MONITORED_INTERFACES, CONF_TRACK_DEVICES]

        if user_input is not None:
            for fields_item in fields_items:
                self.options[fields_item] = self._get_user_input(user_input, fields_item)

            return self.async_create_entry(title="", data=self.options)

        fields = {}

        for fields_item in fields_items:
            current_value = self.options.get(fields_item, "")
            show_clear = len(current_value) > 0
            fields[vol.Optional(fields_item, default=current_value)] = str

            if show_clear:
                fields[vol.Optional(f"{fields_item}{CLEAR_SUFFIX}", default=False)] = bool

        return self.async_show_form(
            step_id="edge_os_additional_settings",
            data_schema=vol.Schema(fields),
            description_placeholders={
                CONF_NAME: self._data.get(CONF_NAME)
            }
        )
