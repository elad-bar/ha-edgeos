"""Storage handlers."""
from __future__ import annotations

from collections.abc import Awaitable, Callable
import logging
import sys

from homeassistant.core import HomeAssistant
from homeassistant.helpers.json import JSONEncoder
from homeassistant.helpers.storage import Store

from ...configuration.models.config_data import ConfigData
from ...core.api.base_api import BaseAPI
from ...core.helpers.enums import ConnectivityStatus
from ..helpers.const import *
from ..models.base_view import EdgeOSBaseView

_LOGGER = logging.getLogger(__name__)


class StorageAPI(BaseAPI):
    _stores: dict[str, Store] | None
    _config_data: ConfigData | None
    _data: dict

    def __init__(
        self,
        hass: HomeAssistant | None,
        async_on_data_changed: Callable[[], Awaitable[None]] | None = None,
        async_on_status_changed: Callable[[ConnectivityStatus], Awaitable[None]]
        | None = None,
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
        result = self.data.get(STORAGE_DATA_UNIT, ATTR_BYTE)

        return result

    @property
    def log_incoming_messages(self):
        result = self.data.get(STORAGE_DATA_LOG_INCOMING_MESSAGES, False)

        return result

    @property
    def consider_away_interval(self):
        result = self.data.get(
            STORAGE_DATA_CONSIDER_AWAY_INTERVAL,
            DEFAULT_CONSIDER_AWAY_INTERVAL.total_seconds(),
        )

        return result

    @property
    def update_entities_interval(self):
        result = self.data.get(
            STORAGE_DATA_UPDATE_ENTITIES_INTERVAL,
            DEFAULT_UPDATE_ENTITIES_INTERVAL.total_seconds(),
        )

        return result

    @property
    def update_api_interval(self):
        result = self.data.get(
            STORAGE_DATA_UPDATE_API_INTERVAL,
            DEFAULT_UPDATE_API_INTERVAL.total_seconds(),
        )

        return result

    async def initialize(self, config_data: ConfigData):
        self._config_data = config_data

        self._initialize_routes()
        self._initialize_storages()

        await self._async_load_configuration()

    def _initialize_storages(self):
        stores = {}

        entry_id = self._config_data.entry.entry_id

        for storage_data_file in STORAGE_DATA_FILES:
            file_name = f"{DOMAIN}.{entry_id}.{storage_data_file}.json"

            stores[storage_data_file] = Store(
                self.hass, STORAGE_VERSION, file_name, encoder=JSONEncoder
            )

        self._stores = stores

    def _initialize_routes(self):
        try:
            main_view_data = {}
            entry_id = self._config_data.entry.entry_id

            for key in STORAGE_API_DATA:
                view = EdgeOSBaseView(self.hass, key, self._get_data, entry_id)

                main_view_data[key] = view.url

                self.hass.http.register_view(view)

            main_view = self.hass.data.get(MAIN_VIEW)

            if main_view is None:
                main_view = EdgeOSBaseView(self.hass, STORAGE_API_LIST, self._get_data)

                self.hass.http.register_view(main_view)
                self.hass.data[MAIN_VIEW] = main_view

            self._data[STORAGE_API_LIST] = main_view_data

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(
                f"Failed to async_component_initialize, error: {ex}, line: {line_number}"
            )

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
                STORAGE_DATA_UPDATE_API_INTERVAL: DEFAULT_UPDATE_API_INTERVAL.total_seconds(),
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

    async def debug_log_api(self, data: dict):
        self._data[STORAGE_API_DATA_API] = data

    async def debug_log_ws(self, data: dict):
        self._data[STORAGE_API_DATA_WS] = data

    async def debug_log_ha(self, data: dict):
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

            else:
                clean_data[key] = data.get(key)

        self._data[STORAGE_API_DATA_HA] = clean_data

    def _get_data(self, key):
        is_list = key == STORAGE_API_LIST

        data = {} if is_list else self._data.get(key)

        if is_list:
            raw_data = self._data.get(key)
            current_entry_id = self._config_data.entry.entry_id

            for entry_id in self.hass.data[DATA].keys():
                entry_data = {}

                for raw_data_key in raw_data:
                    url_raw = raw_data.get(raw_data_key)
                    url = url_raw.replace(current_entry_id, entry_id)

                    entry_data[raw_data_key] = url

                data[entry_id] = entry_data

        return data
