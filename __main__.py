import sys
import asyncio
import logging

from local_consts import *

from custom_components.edgeos import EMPTY_STRING, ATTR_WEB_SOCKET_MESSAGES_HANDLED_PERCENTAGE, \
    ATTR_WEB_SOCKET_MESSAGES_IGNORED, ATTR_WEB_SOCKET_MESSAGES_RECEIVED
from custom_components.edgeos.managers.configuration_manager import ConfigManager
from custom_components.edgeos.managers.data_manager import EdgeOSData
from custom_components.edgeos.managers.password_manager import PasswordManager
from custom_components.edgeos.models.config_data import ConfigData
from homeassistant.core import HomeAssistant

log_level = logging.DEBUG

root = logging.getLogger()
root.setLevel(log_level)

stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setLevel(log_level)
formatter = logging.Formatter('%(asctime)s %(levelname)s %(name)s %(message)s')
stream_handler.setFormatter(formatter)
root.addHandler(stream_handler)

_LOGGER = logging.getLogger(__name__)

loop = asyncio.get_event_loop()


class Test:
    messages: int = 0

    def __init__(self):
        self._instance = None

        self._hass = None

        self._password_manager = None
        self._config_manager = None
        self._data_manager = None

    async def init(self):
        self._instance = None

        self._hass = HomeAssistant()
        self._hass.config.config_dir = EMPTY_STRING

        self._password_manager = PasswordManager(self._hass)
        self._config_manager = ConfigManager(self._password_manager)

        config_data: ConfigData = ConfigData()
        config_data.password_clear_text = PASSWORD
        config_data.password = self._password_manager.encrypt(PASSWORD)
        config_data.host = HOSTNAME
        config_data.port = PORT
        config_data.username = USERNAME

        self._config_manager.set_data(config_data)

        self._data_manager = EdgeOSData(self._hass, self._config_manager, self.update)

    async def terminate(self):
        await self._data_manager.terminate()

    def update(self):
        system_data = self._data_manager.system_data

        messages_received = system_data.get(ATTR_WEB_SOCKET_MESSAGES_RECEIVED)
        messages_ignored = system_data.get(ATTR_WEB_SOCKET_MESSAGES_IGNORED)
        messages_handled_percentage = system_data.get(ATTR_WEB_SOCKET_MESSAGES_HANDLED_PERCENTAGE)

        data = {
            ATTR_WEB_SOCKET_MESSAGES_RECEIVED: messages_received,
            ATTR_WEB_SOCKET_MESSAGES_IGNORED: messages_ignored,
            ATTR_WEB_SOCKET_MESSAGES_HANDLED_PERCENTAGE: messages_handled_percentage
        }

        _LOGGER.info(data)

    async def initialize(self):
        await self._data_manager.initialize()

        print("exit")


if __name__ == "__main__":
    t = Test()
    loop.run_until_complete(t.init())
    loop.run_until_complete(t.initialize())
