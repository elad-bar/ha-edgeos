"""Storage handlers."""
from __future__ import annotations

from collections.abc import Awaitable, Callable
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.json import JSONEncoder
from homeassistant.helpers.storage import Store

from ...configuration.models.config_data import ConfigData
from ...core.api.base_api import BaseAPI
from ...core.helpers.enums import ConnectivityStatus
from ..helpers.const import *

_LOGGER = logging.getLogger(__name__)


class StorageAPI(BaseAPI):
    _stores: dict[str, Store] | None
    _config_data: ConfigData | None
    _data: dict

    def __init__(self,
                 hass: HomeAssistant | None,
                 async_on_data_changed: Callable[[], Awaitable[None]] | None = None,
                 async_on_status_changed: Callable[[ConnectivityStatus], Awaitable[None]] | None = None
                 ):

        super().__init__(hass, async_on_data_changed, async_on_status_changed)

        self._config_data = None
        self._stores = None
        self._data = {}

    @property
    def _storage_config(self) -> Store:
        storage = self._stores.get(STORAGE_DATA_FILE_CONFIG)

        return storage

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
        result = self.data.get(STORAGE_DATA_UNIT, ATTR_BYTE).replace(ATTR_BYTE[1:], "")

        return result

    @property
    def log_incoming_messages(self):
        result = self.data.get(STORAGE_DATA_LOG_INCOMING_MESSAGES, False)

        return result

    @property
    def consider_away_interval(self):
        result = self.data.get(STORAGE_DATA_CONSIDER_AWAY_INTERVAL, DEFAULT_CONSIDER_AWAY_INTERVAL.total_seconds())

        return result

    @property
    def update_entities_interval(self):
        result = self.data.get(STORAGE_DATA_UPDATE_ENTITIES_INTERVAL, DEFAULT_UPDATE_ENTITIES_INTERVAL.total_seconds())

        return result

    @property
    def update_api_interval(self):
        result = self.data.get(STORAGE_DATA_UPDATE_API_INTERVAL, DEFAULT_UPDATE_API_INTERVAL.total_seconds())

        return result

    async def initialize(self, config_data: ConfigData):
        self._config_data = config_data

        self._initialize_storages()

        await self._async_load_configuration()

    def _initialize_storages(self):
        stores = {}

        entry_id = self._config_data.entry.entry_id

        for storage_data_file in STORAGE_DATA_FILES:
            file_name = f"{DOMAIN}.{entry_id}.{storage_data_file}.json"

            stores[storage_data_file] = Store(self.hass, STORAGE_VERSION, file_name, encoder=JSONEncoder)

        self._stores = stores

    async def _async_load_configuration(self):
        """Load the retained data from store and return de-serialized data."""
        self.data = await self._storage_config.async_load()

        if self.data is None:
            self.data = {
                STORAGE_DATA_MONITORED_INTERFACES: {},
                STORAGE_DATA_MONITORED_DEVICES: {},
                STORAGE_DATA_UNIT: ATTR_BYTE,
                STORAGE_DATA_LOG_INCOMING_MESSAGES: False,
                STORAGE_DATA_CONSIDER_AWAY_INTERVAL: DEFAULT_CONSIDER_AWAY_INTERVAL.total_seconds(),
                STORAGE_DATA_UPDATE_ENTITIES_INTERVAL: DEFAULT_UPDATE_ENTITIES_INTERVAL.total_seconds(),
                STORAGE_DATA_UPDATE_API_INTERVAL: DEFAULT_UPDATE_API_INTERVAL.total_seconds()
            }

            await self._async_save()

        _LOGGER.debug(f"Loaded configuration data: {self.data}")

        await self.set_status(ConnectivityStatus.Connected)
        await self.fire_data_changed_event()

    async def _async_save(self):
        """Generate dynamic data to store and save it to the filesystem."""
        _LOGGER.info(f"Save configuration, Data: {self.data}")

        await self._storage_config.async_save(self.data)

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

    async def set_consider_away_interval(self, interval: int):
        _LOGGER.debug(f"Changing {STORAGE_DATA_CONSIDER_AWAY_INTERVAL}: {interval}")

        self.data[STORAGE_DATA_CONSIDER_AWAY_INTERVAL] = interval

        await self._async_save()

    async def set_update_entities_interval(self, interval: int):
        _LOGGER.debug(f"Changing {STORAGE_DATA_UPDATE_ENTITIES_INTERVAL}: {interval}")

        self.data[STORAGE_DATA_UPDATE_ENTITIES_INTERVAL] = interval

        await self._async_save()

    async def set_update_api_interval(self, interval: int):
        _LOGGER.debug(f"Changing {STORAGE_DATA_UPDATE_API_INTERVAL}: {interval}")

        self.data[STORAGE_DATA_UPDATE_API_INTERVAL] = interval

        await self._async_save()
