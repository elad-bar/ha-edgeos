from __future__ import annotations

import logging
from os import path, remove
import sys

from cryptography.fernet import Fernet

from homeassistant.core import HomeAssistant

from ..helpers.const import DOMAIN_KEY_FILE
from ..managers.storage_manager import StorageManager
from ..models.storage_data import StorageData

_LOGGER = logging.getLogger(__name__)


class PasswordManager:
    data: StorageData | None
    hass: HomeAssistant
    crypto: Fernet

    def __init__(self, hass: HomeAssistant):
        self.hass = hass
        self.data = None

    async def initialize(self):
        try:
            if self.data is None:
                storage_manager = StorageManager(self.hass)

                self.data = await storage_manager.async_load_from_store()

                if self.data.key is None:
                    legacy_key_path = self.hass.config.path(DOMAIN_KEY_FILE)

                    if path.exists(legacy_key_path):
                        with open(legacy_key_path, "rb") as file:
                            self.data.key = file.read().decode("utf-8")

                        remove(legacy_key_path)
                    else:
                        self.data.key = Fernet.generate_key().decode("utf-8")

                    await storage_manager.async_save_to_store(self.data)

                self.crypto = Fernet(self.data.key.encode())
        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(
                f"Failed to initialize Password Manager, error: {ex}, line: {line_number}"
            )

    def set(self, data: str) -> str:
        if data is not None:
            data = self.crypto.encrypt(data.encode()).decode()

        return data

    def get(self, data: str) -> str:
        if data is not None and len(data) > 0:
            data = self.crypto.decrypt(data.encode()).decode()

        return data
