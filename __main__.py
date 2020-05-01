import asyncio
import logging

from homeassistant.core import HomeAssistant

from custom_components.edgeos.managers.configuration_manager import ConfigManager
from custom_components.edgeos.managers.data_manager import EdgeOSData
from custom_components.edgeos.managers.password_manager import PasswordManager
from custom_components.edgeos.models.config_data import ConfigData

from test_consts import *

logging.basicConfig(filename="log.txt", filemode="a", level="DEBUG")

_LOGGER = logging.getLogger(__name__)

loop = asyncio.get_event_loop()


class Test:
    def __init__(self):
        self._instance = None

        self._hass = HomeAssistant()
        self._hass.config.config_dir = ""

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

    def update(self):
        _LOGGER.info(self._data_manager.edgeos_data)
        _LOGGER.info(self._data_manager.system_data)

    async def initialize(self):
        await self._data_manager.initialize()

        print("exit")


if __name__ == "__main__":
    t = Test()
    loop.run_until_complete(t.initialize())





