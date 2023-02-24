"""Config flow to configure."""
from __future__ import annotations

import logging

from cryptography.fernet import InvalidToken
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback

from .component.api.api import IntegrationAPI
from .configuration.helpers.const import DEFAULT_NAME, DOMAIN
from .configuration.helpers.exceptions import AlreadyExistsError, LoginError
from .configuration.managers.configuration_manager import ConfigurationManager

_LOGGER = logging.getLogger(__name__)


@config_entries.HANDLERS.register(DOMAIN)
class DomainFlowHandler(config_entries.ConfigFlow):
    """Handle a domain config flow."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    def __init__(self):
        super().__init__()

        self._config_manager: ConfigurationManager | None = None

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return DomainOptionsFlowHandler(config_entry)

    async def async_step_user(self, user_input=None):
        """Handle a flow start."""
        _LOGGER.debug(f"Starting async_step_user of {DEFAULT_NAME}")

        api = IntegrationAPI(self.hass)
        self._config_manager = ConfigurationManager(self.hass, api)

        await self._config_manager.initialize()

        errors = None

        if user_input is not None:
            try:
                await self._config_manager.validate(user_input)

                _LOGGER.debug("User inputs are valid")

                return self.async_create_entry(title=DEFAULT_NAME, data=user_input)
            except LoginError as lex:
                errors = lex.errors

            except InvalidToken:
                errors = {"base": "corrupted_encryption_key"}

            except AlreadyExistsError:
                errors = {"base": "already_configured"}

            if errors is not None:
                error_message = errors.get("base")

                _LOGGER.warning(f"Failed to create integration, Error: {error_message}")

        new_user_input = self._config_manager.get_data_fields(user_input)

        schema = vol.Schema(new_user_input)

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)


class DomainOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle domain options."""

    def __init__(self, config_entry: ConfigEntry):
        """Initialize domain options flow."""
        super().__init__()

        self._config_entry = config_entry
        self._config_manager: ConfigurationManager | None = None

    async def async_step_init(self, user_input=None):
        """Manage the domain options."""
        _LOGGER.info(f"Starting additional settings step: {user_input}")

        api = IntegrationAPI(self.hass)
        self._config_manager = ConfigurationManager(self.hass, api)
        await self._config_manager.initialize()

        errors = None

        if user_input is not None:
            try:
                await self._config_manager.validate(user_input)

                _LOGGER.debug("User inputs are valid")

                options = self._config_manager.remap_entry_data(
                    self._config_entry, user_input
                )

                return self.async_create_entry(
                    title=self._config_entry.title, data=options
                )
            except LoginError as lex:
                errors = lex.errors

            except InvalidToken:
                errors = {"base": "corrupted_encryption_key"}

            except AlreadyExistsError:
                errors = {"base": "already_configured"}

            if errors is not None:
                error_message = errors.get("base")

                _LOGGER.warning(f"Failed to create integration, Error: {error_message}")

        new_user_input = self._config_manager.get_options_fields(
            self._config_entry.data
        )

        schema = vol.Schema(new_user_input)

        return self.async_show_form(step_id="init", data_schema=schema, errors=errors)
