from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry

from ..helpers.const import *


class ConfigData:
    host: str | None
    port: int
    username: str | None
    password: str | None
    entry: ConfigEntry | None

    update_entities_interval: int
    update_api_interval: int
    consider_away_interval: int

    def __init__(self):
        self.host = ""
        self.port = 0
        self.username = None
        self.password = None
        self.update_entities_interval = DEFAULT_UPDATE_ENTITIES_INTERVAL
        self.update_api_interval = DEFAULT_UPDATE_API_INTERVAL
        self.consider_away_interval = DEFAULT_CONSIDER_AWAY_INTERVAL
        self.entry = None

    @property
    def url(self):
        url = API_URL_TEMPLATE.format(self.host)

        return url

    @staticmethod
    def from_dict(data: dict[str, Any] = None) -> ConfigData:
        result = ConfigData()

        if data is not None:
            result.host = data.get(CONF_HOST)
            result.port = data.get(CONF_PORT, DEFAULT_PORT)
            result.username = data.get(CONF_USERNAME)
            result.password = data.get(CONF_PASSWORD)
            result.update_api_interval = data.get(CONF_UPDATE_API_INTERVAL, DEFAULT_UPDATE_API_INTERVAL)
            result.update_entities_interval = data.get(CONF_UPDATE_ENTITIES_INTERVAL, DEFAULT_UPDATE_ENTITIES_INTERVAL)
            result.consider_away_interval = data.get(CONF_CONSIDER_AWAY_INTERVAL, DEFAULT_CONSIDER_AWAY_INTERVAL)

        return result

    def to_dict(self):
        obj = {
            CONF_HOST: self.host,
            CONF_PORT: self.port,
            CONF_USERNAME: self.username,
            CONF_PASSWORD: self.password,
            CONF_UPDATE_API_INTERVAL: self.update_api_interval,
            CONF_UPDATE_ENTITIES_INTERVAL: self.update_entities_interval,
            CONF_CONSIDER_AWAY_INTERVAL: self.consider_away_interval,
        }

        return obj

    def __repr__(self):
        to_string = f"{self.to_dict()}"

        return to_string
