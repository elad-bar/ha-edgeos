import logging
import sys

from cryptography.fernet import Fernet, InvalidToken

from homeassistant.config_entries import STORAGE_VERSION
from homeassistant.const import CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.helpers.json import JSONEncoder
from homeassistant.helpers.storage import Store

from ..common.consts import CONFIGURATION_FILE, INVALID_TOKEN_SECTION, STORAGE_DATA_KEY

_LOGGER = logging.getLogger(__name__)


class PasswordManager:
    _encryption_key: str | None
    _crypto: Fernet | None
    _entry_id: str

    def __init__(self, hass: HomeAssistant | None, entry_id: str = ""):
        self._hass = hass
        self._entry_id = entry_id

        self._encryption_key = None
        self._crypto = None

        if hass is None:
            self._store = None

        else:
            self._store = Store(
                hass, STORAGE_VERSION, CONFIGURATION_FILE, encoder=JSONEncoder
            )

    async def initialize(self):
        try:
            await self._load_encryption_key()

        except InvalidToken:
            _LOGGER.error(
                f"Invalid encryption key, Please follow instructions in {INVALID_TOKEN_SECTION}"
            )

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(
                f"Failed to initialize configuration manager, Error: {ex}, Line: {line_number}"
            )

    @staticmethod
    async def decrypt(hass: HomeAssistant, data: dict, entry_id: str = "") -> None:
        instance = PasswordManager(hass, entry_id)

        await instance.initialize()

        password = data.get(CONF_PASSWORD)
        password_decrypted = instance._decrypt(password)
        data[CONF_PASSWORD] = password_decrypted

    @staticmethod
    async def encrypt(hass: HomeAssistant, data: dict, entry_id: str = "") -> None:
        instance = PasswordManager(hass, entry_id)

        await instance.initialize()

        if CONF_PASSWORD in data:
            password = data.get(CONF_PASSWORD)
            password_encrypted = instance._encrypt(password)

            data[CONF_PASSWORD] = password_encrypted

    async def _load_encryption_key(self):
        store_data = None

        if self._store is not None:
            store_data = await self._store.async_load()

        if store_data is not None:
            if STORAGE_DATA_KEY in store_data:
                self._encryption_key = store_data.get(STORAGE_DATA_KEY)

            else:
                for store_data_key in store_data:
                    if store_data_key == self._entry_id:
                        entry_configuration = store_data[store_data_key]

                        if STORAGE_DATA_KEY in entry_configuration:
                            self._encryption_key = entry_configuration.get(
                                STORAGE_DATA_KEY
                            )

                            entry_configuration.pop(STORAGE_DATA_KEY)

        if self._encryption_key is None:
            self._encryption_key = Fernet.generate_key().decode("utf-8")

        await self._save()

        self._crypto = Fernet(self._encryption_key.encode())

    async def _save(self):
        if self._store is None:
            return

        store_data = await self._store.async_load()

        if store_data is None:
            store_data = {}

        if store_data.get(STORAGE_DATA_KEY) != self._encryption_key:
            store_data[STORAGE_DATA_KEY] = self._encryption_key

            await self._store.async_save(store_data)

    def _encrypt(self, data: str) -> str:
        if data is not None:
            data = self._crypto.encrypt(data.encode()).decode()

        return data

    def _decrypt(self, data: str) -> str:
        if data is not None and len(data) > 0:
            data = self._crypto.decrypt(data.encode()).decode()

        return data
