from __future__ import annotations

import logging
import sys
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from ...core.api.base_api import BaseAPI
from ...core.helpers.const import *
from ...core.helpers.enums import ConnectivityStatus
from ...core.managers.password_manager import PasswordManager
from ..helpers.exceptions import LoginError
from ..models.config_data import ConfigData

_LOGGER = logging.getLogger(__name__)


class ConfigurationManager:
    password_manager: PasswordManager
    config: dict[str, ConfigData]
    api: BaseAPI | None

    def __init__(self, hass: HomeAssistant, api: BaseAPI | None = None):
        self.hass = hass
        self.config = {}
        self.password_manager = PasswordManager(hass)
        self.api = api

    async def initialize(self):
        await self.password_manager.initialize()

    def get(self, entry_id: str):
        config = self.config.get(entry_id)

        return config

    async def load(self, entry: ConfigEntry):
        try:
            await self.initialize()

            config = {k: entry.data[k] for k in entry.data}

            if CONF_PASSWORD in config:
                encrypted_password = config[CONF_PASSWORD]

                config[CONF_PASSWORD] = self.password_manager.get(encrypted_password)

            config_data = ConfigData.from_dict(config)

            if config_data is not None:
                config_data.entry = entry

                self.config[entry.entry_id] = config_data
        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(
                f"Failed to load configuration, error: {str(ex)}, line: {line_number}"
            )

    async def validate(self, data: dict[str, Any]):
        if self.api is None:
            _LOGGER.error("Validate configuration is not supported through that flow")
            return

        _LOGGER.debug("Validate login")

        await self.api.validate(data)

        errors = self._get_config_errors()

        if errors is None:
            password = data[CONF_PASSWORD]

            data[CONF_PASSWORD] = self.password_manager.set(password)

        else:
            raise LoginError(errors)

    def _get_config_errors(self):
        result = None
        status_mapping = {
            str(ConnectivityStatus.NotConnected): "invalid_server_details",
            str(ConnectivityStatus.Connecting): "invalid_server_details",
            str(ConnectivityStatus.Failed): "invalid_server_details",
            str(ConnectivityStatus.NotFound): "invalid_server_details",
            str(ConnectivityStatus.MissingAPIKey): "missing_permanent_api_key",
            str(ConnectivityStatus.InvalidCredentials): "invalid_admin_credentials",
            str(ConnectivityStatus.TemporaryConnected): "missing_permanent_api_key",
        }

        status_description = status_mapping.get(str(self.api.status))

        if status_description is not None:
            result = {"base": status_description}

        return result

    @staticmethod
    def get_data_fields(user_input: dict[str, Any] | None) -> dict[vol.Marker, Any]:
        if user_input is None:
            user_input = ConfigData.from_dict().to_dict()

        fields = {
            vol.Required(CONF_HOST, default=user_input.get(CONF_HOST)): str,
            vol.Required(CONF_PORT, default=user_input.get(CONF_PORT)): int,
            vol.Required(CONF_USERNAME, default=user_input.get(CONF_USERNAME)): str,
            vol.Required(CONF_PASSWORD, default=user_input.get(CONF_PASSWORD)): str,
        }

        return fields

    def get_options_fields(self, user_input: dict[str, Any]) -> dict[vol.Marker, Any]:
        if user_input is None:
            data = ConfigData.from_dict().to_dict()

        else:
            data = {k: user_input[k] for k in user_input}
            encrypted_password = data.get(CONF_PASSWORD)

            data[CONF_PASSWORD] = self.password_manager.get(encrypted_password)

        fields = {
            vol.Required(CONF_HOST, default=data.get(CONF_HOST)): str,
            vol.Required(CONF_PORT, default=data.get(CONF_PORT)): int,
            vol.Required(CONF_USERNAME, default=data.get(CONF_USERNAME)): str,
            vol.Required(CONF_PASSWORD, default=data.get(CONF_PASSWORD)): str,

            vol.Required(CONF_UPDATE_API_INTERVAL,
                         default=data.get(CONF_UPDATE_API_INTERVAL, DEFAULT_UPDATE_API_INTERVAL)): int,

            vol.Required(CONF_UPDATE_ENTITIES_INTERVAL,
                         default=data.get(CONF_UPDATE_ENTITIES_INTERVAL, DEFAULT_UPDATE_ENTITIES_INTERVAL)): int,

            vol.Required(CONF_CONSIDER_AWAY_INTERVAL,
                         default=data.get(CONF_CONSIDER_AWAY_INTERVAL, DEFAULT_CONSIDER_AWAY_INTERVAL)): int
        }

        return fields

    def remap_entry_data(self, entry: ConfigEntry, options: dict[str, Any]) -> dict[str, Any]:
        config_options = {}
        config_data = {}

        for key in options:
            if key in DATA_KEYS:
                config_data[key] = options.get(key, entry.data.get(key))

            else:
                config_options[key] = options.get(key)

        config_entries = self.hass.config_entries
        config_entries.async_update_entry(entry, data=config_data)

        return config_options
