"""Config flow to configure HPPrinter."""
import logging

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback

from . import get_ha
from .helpers.const import *
from .managers.config_flow_manager import ConfigFlowManager
from .managers.home_assistant import EdgeOSHomeAssistant

_LOGGER = logging.getLogger(__name__)

BASE_FIELDS = {
    vol.Required(CONF_NAME, DEFAULT_NAME): str,
    vol.Required(CONF_HOST): str,
    vol.Required(CONF_USERNAME): str,
    vol.Required(CONF_PASSWORD): str,
    vol.Optional(CONF_UNIT, default=ATTR_BYTE): vol.In(ALLOWED_UNITS_LIST),
}


@config_entries.HANDLERS.register(DOMAIN)
class EdgeOSFlowHandler(config_entries.ConfigFlow):
    """Handle a EdgeOS config flow."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    def __init__(self):
        super().__init__()

        self._config_flow = ConfigFlowManager()

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return EdgeOSOptionsFlowHandler(config_entry)

    async def async_step_user(self, user_input=None):
        """Handle a flow start."""
        _LOGGER.debug(f"Starting async_step_user of {DEFAULT_NAME}")

        errors = None

        self._config_flow.initialize(self.hass)

        if user_input is not None:
            if CONF_PASSWORD in user_input:
                password_clear_text = user_input[CONF_PASSWORD]
                password = self._config_flow.password_manager.encrypt(
                    password_clear_text
                )

                user_input[CONF_PASSWORD] = password

            self._config_flow.update_data(user_input, True)

            name = self._config_flow.config_data.name

            ha = get_ha(self.hass, self._config_flow.config_data.name)

            if ha is None:
                errors = await self._config_flow.validate_login()
            else:
                _LOGGER.warning(f"EdgeOS ({name}) already configured")

                return self.async_abort(
                    reason="already_configured", description_placeholders=user_input
                )

            if errors is None:
                _LOGGER.info(f"Storing configuration data: {user_input}")

                return self.async_create_entry(title=name, data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=vol.Schema(BASE_FIELDS), errors=errors
        )

    async def async_step_import(self, info):
        """Import existing configuration from Z-Wave."""
        _LOGGER.debug(f"Starting async_step_import of {DEFAULT_NAME}")

        title = f"{DEFAULT_NAME} (import from configuration.yaml)"

        return self.async_create_entry(title=title, data=info)


class EdgeOSOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle Plex options."""

    def __init__(self, config_entry: ConfigEntry):
        """Initialize EdgeOS options flow."""
        super().__init__()

        self._config_flow = ConfigFlowManager(config_entry)

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

        available_items = {OPTION_EMPTY: OPTION_EMPTY}

        for item_key in all_items:
            item = all_items[item_key]
            item_name = item.get(CONF_NAME)

            available_items[item_key] = item_name

        return available_items

    async def async_step_edge_os_additional_settings(self, user_input=None):
        _LOGGER.info(f"async_step_edge_os_additional_settings: {user_input}")

        self._config_flow.initialize(self.hass)

        if user_input is not None:
            self._config_flow.update_options(user_input, True)

            _LOGGER.info(f"Storing configuration options: {user_input}")

            return self.async_create_entry(title="", data=self._config_flow.options)

        config_data = self._config_flow.config_data
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
            }
        )

        return self.async_show_form(
            step_id="edge_os_additional_settings",
            data_schema=schema,
            description_placeholders=self._config_flow.data,
        )
