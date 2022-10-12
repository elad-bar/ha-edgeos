"""Storage handlers."""
from __future__ import annotations

from datetime import datetime
import json
import logging
from typing import Awaitable, Callable

from homeassistant.core import HomeAssistant
from homeassistant.helpers.json import JSONEncoder
from homeassistant.helpers.storage import Store

from ...configuration.models.config_data import ConfigData
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

        self._storages = None

    @property
    def _storage_config(self) -> Store:
        storage = self._storages.get(STORAGE_DATA_FILE_CONFIG)

        return storage

    @property
    def _storage_api(self) -> Store:
        storage = self._storages.get(STORAGE_DATA_FILE_API_DEBUG)

        return storage

    @property
    def _storage_ws(self) -> Store:
        storage = self._storages.get(STORAGE_DATA_FILE_WS_DEBUG)

        return storage

    @property
    def _storage_ha(self) -> Store:
        storage = self._storages.get(STORAGE_DATA_FILE_HA_DEBUG)

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
        storages = {}
        entry_id = config_data.entry.entry_id

        for storage_data_file in STORAGE_DATA_FILES:
            file_name = f"{DOMAIN}.{entry_id}.{storage_data_file}.json"

            storages[storage_data_file] = Store(self.hass, STORAGE_VERSION, file_name, encoder=JSONEncoder)

        self._storages = storages

        await self._async_load_configuration()

    async def _async_load_configuration(self):
        """Load the retained data from store and return de-serialized data."""
        self.data = await self._storage_config.async_load()

        if self.data is None:
            self.data = {
                STORAGE_DATA_MONITORED_INTERFACES: {},
                STORAGE_DATA_MONITORED_DEVICES: {},
                STORAGE_DATA_UNIT: ATTR_BYTE,
                STORAGE_DATA_LOG_INCOMING_MESSAGES: False,
                STORAGE_DATA_STORE_DEBUG_DATA: False,
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

    async def set_store_debug_data(self, enabled: bool):
        _LOGGER.debug(f"Set store debug data to {enabled}")

        self.data[STORAGE_DATA_STORE_DEBUG_DATA] = enabled

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

    async def debug_log_api(self, data: dict):
        if self.store_debug_data and data is not None:
            await self._storage_api.async_save(self._get_json_data(data))

    async def debug_log_ws(self, data: dict):
        if self.store_debug_data and data is not None:
            await self._storage_ws.async_save(self._get_json_data(data))

    async def debug_log_ha(self, data: dict):
        if self.store_debug_data and data is not None:
            clean_data = {}
            for key in data:
                if key in [DEVICE_LIST, API_DATA_INTERFACES]:
                    new_item = {}
                    items = data.get(key, {})

                    for item_key in items:
                        item = items.get(item_key)
                        new_item[item_key] = item.to_dict()

                    clean_data[key] = new_item

                elif key in [API_DATA_SYSTEM]:
                    item = data.get(key)
                    clean_data[key] = item.to_dict()

            await self._storage_ha.async_save(self._get_json_data(clean_data))

    def _get_json_data(self, data: dict):
        json_data = json.dumps(data, default=self.json_converter, sort_keys=True, indent=4)

        result = json.loads(json_data)

        return result

    @staticmethod
    def json_converter(data):
        if isinstance(data, datetime):
            return data.__str__()
        if isinstance(data, dict):
            return data.__dict__
