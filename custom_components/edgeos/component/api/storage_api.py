"""Storage handlers."""
from __future__ import annotations

import logging
from typing import Awaitable, Callable

from homeassistant.core import HomeAssistant
from homeassistant.helpers.json import JSONEncoder
from homeassistant.helpers.storage import Store

from ...core.api.base_api import BaseAPI
from ...core.helpers.enums import ConnectivityStatus
from ..helpers.const import *

_LOGGER = logging.getLogger(__name__)


class StorageAPI(BaseAPI):
    _storage: Store

    def __init__(self,
                 hass: HomeAssistant,
                 async_on_data_changed: Callable[[], Awaitable[None]] | None = None,
                 async_on_status_changed: Callable[[ConnectivityStatus], Awaitable[None]] | None = None
                 ):

        super().__init__(hass, async_on_data_changed, async_on_status_changed)

        self._storage = Store(self.hass, STORAGE_VERSION, self._file_name, encoder=JSONEncoder)
        self._storage_ws = Store(self.hass, STORAGE_VERSION, self._ws_file_name, encoder=JSONEncoder)
        self._storage_api = Store(self.hass, STORAGE_VERSION, self._api_file_name, encoder=JSONEncoder)

    @property
    def _file_name(self):
        file_name = f"{DOMAIN}.config.json"

        return file_name

    @property
    def _ws_file_name(self):
        file_name = f"{DOMAIN}.ws.debug.json"

        return file_name

    @property
    def _api_file_name(self):
        file_name = f"{DOMAIN}.api.debug.json"

        return file_name

    @property
    def monitored_interfaces(self):
        result = self.data.get(STORAGE_DATA_MONITORED_INTERFACES, {})

        return result

    @property
    def monitored_devices(self):
        result = self.data.get(STORAGE_DATA_MONITORED_DEVICES, {})

        return result

    @property
    def unit(self):
        result = self.data.get(STORAGE_DATA_UNIT, ATTR_BYTE)

        return result

    @property
    def log_incoming_messages(self):
        result = self.data.get(STORAGE_DATA_LOG_INCOMING_MESSAGES, False)

        return result

    @property
    def store_debug_data(self):
        result = self.data.get(STORAGE_DATA_STORE_DEBUG_DATA, False)

        return result

    async def initialize(self):
        await self._async_load()

    async def _async_load(self):
        """Load the retained data from store and return de-serialized data."""
        _LOGGER.info(f"Loading configuration from {self._file_name}")

        self.data = await self._storage.async_load()

        if self.data is None:
            self.data = {
                STORAGE_DATA_MONITORED_INTERFACES: {},
                STORAGE_DATA_MONITORED_DEVICES: {},
                STORAGE_DATA_UNIT: ATTR_BYTE,
                STORAGE_DATA_LOG_INCOMING_MESSAGES: False,
                STORAGE_DATA_STORE_DEBUG_DATA: False
            }

            await self._async_save()

        _LOGGER.debug(f"Loaded configuration data: {self.data}")

        await self.set_status(ConnectivityStatus.Connected)
        await self.fire_data_changed_event()

    async def _async_save(self):
        """Generate dynamic data to store and save it to the filesystem."""
        _LOGGER.info(f"Save configuration to {self._file_name}, Data: {self.data}")

        await self._storage.async_save(self.data)

        await self.fire_data_changed_event()

    async def set_monitored_interface(self, interface_name: str, is_enabled: bool):
        _LOGGER.debug(f"Set monitored interface {interface_name} to {is_enabled}")

        self.data[STORAGE_DATA_MONITORED_INTERFACES][interface_name] = is_enabled

        await self._async_save()

    async def set_monitored_device(self, device_name: str, is_enabled: bool):
        _LOGGER.debug(f"Set monitored interface {device_name} to {is_enabled}")

        self.data[STORAGE_DATA_MONITORED_DEVICES][device_name] = is_enabled

        await self._async_save()

    async def set_unit(self, unit: str):
        _LOGGER.debug(f"Set unit to {unit}")

        self.data[STORAGE_DATA_UNIT] = unit

        await self._async_save()

    async def set_log_incoming_messages(self, enabled: bool):
        _LOGGER.debug(f"Set log incoming messages to {enabled}")

        self.data[STORAGE_DATA_LOG_INCOMING_MESSAGES] = enabled

        await self._async_save()

    async def set_store_debug_data(self, enabled: bool):
        _LOGGER.debug(f"Set store debug data to {enabled}")

        self.data[STORAGE_DATA_STORE_DEBUG_DATA] = enabled

        await self._async_save()

    async def debug_log_api(self, data: dict):
        if self.store_debug_data:
            await self._storage_api.async_save(data)

    async def debug_log_ws(self, data: dict):
        if self.store_debug_data:
            await self._storage_ws.async_save(data)
