"""Config flow to configure."""
from __future__ import annotations

import logging

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback

from .common.consts import DOMAIN
from .managers.flow_manager import IntegrationFlowManager

_LOGGER = logging.getLogger(__name__)


@config_entries.HANDLERS.register(DOMAIN)
class DomainFlowHandler(config_entries.ConfigFlow):
    """Handle a domain config flow."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    def __init__(self):
        super().__init__()

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return DomainOptionsFlowHandler(config_entry)

    async def async_step_user(self, user_input=None):
        """Handle a flow start."""
        flow_manager = IntegrationFlowManager(self.hass, self)

        return await flow_manager.async_step(user_input)


class DomainOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle domain options."""

    _config_entry: ConfigEntry

    def __init__(self, config_entry: ConfigEntry):
        """Initialize domain options flow."""
        super().__init__()

        self._config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the domain options."""
        flow_manager = IntegrationFlowManager(self.hass, self, self._config_entry)

        return await flow_manager.async_step(user_input)
