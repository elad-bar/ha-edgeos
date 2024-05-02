from urllib.parse import urlparse

import voluptuous as vol
from voluptuous import Schema

from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PATH,
    CONF_PORT,
    CONF_SSL,
    CONF_USERNAME,
)

from ..common.consts import (
    API_URL_TEMPLATE,
    CONF_TITLE,
    DEFAULT_NAME,
    WEBSOCKET_URL_TEMPLATE,
)

DATA_KEYS = [CONF_HOST, CONF_PORT, CONF_SSL, CONF_PATH, CONF_USERNAME, CONF_PASSWORD]


class ConfigData:
    _hostname: str | None
    _username: str | None
    _password: str | None

    def __init__(self):
        self._hostname = None
        self._username = None
        self._password = None

    @property
    def hostname(self) -> str:
        hostname = self._hostname

        return hostname

    @property
    def username(self) -> str:
        username = self._username

        return username

    @property
    def password(self) -> str:
        password = self._password

        return password

    @property
    def api_url(self):
        url = API_URL_TEMPLATE.format(self._hostname)

        return url

    @property
    def ws_url(self):
        url = urlparse(self.api_url)

        ws_url = WEBSOCKET_URL_TEMPLATE.format(url.netloc)

        return ws_url

    def update(self, data: dict):
        self._password = data.get(CONF_PASSWORD)
        self._username = data.get(CONF_USERNAME)
        self._hostname = data.get(CONF_HOST)

    def to_dict(self):
        obj = {
            CONF_USERNAME: self.username,
            CONF_HOST: self.hostname,
        }

        return obj

    def __repr__(self):
        to_string = f"{self.to_dict()}"

        return to_string

    @staticmethod
    def default_schema(user_input: dict | None) -> Schema:
        if user_input is None:
            user_input = {}

        new_user_input = {
            vol.Required(
                CONF_TITLE, default=user_input.get(CONF_TITLE, DEFAULT_NAME)
            ): str,
            vol.Required(CONF_HOST, default=user_input.get(CONF_HOST)): str,
            vol.Required(CONF_USERNAME, default=user_input.get(CONF_USERNAME)): str,
            vol.Required(CONF_PASSWORD, default=user_input.get(CONF_PASSWORD)): str,
        }

        schema = vol.Schema(new_user_input)

        return schema
