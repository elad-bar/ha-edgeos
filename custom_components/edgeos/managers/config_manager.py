import json
import logging
import sys

from cryptography.fernet import InvalidToken

from homeassistant.config_entries import STORAGE_VERSION, ConfigEntry
from homeassistant.const import CONF_NAME, CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import translation
from homeassistant.helpers.json import JSONEncoder
from homeassistant.helpers.storage import Store

from ..common.consts import (
    CONFIGURATION_FILE,
    DEFAULT_CONSIDER_AWAY_INTERVAL,
    DEFAULT_NAME,
    DEFAULT_UPDATE_API_INTERVAL,
    DEFAULT_UPDATE_ENTITIES_INTERVAL,
    DOMAIN,
    INVALID_TOKEN_SECTION,
    STORAGE_DATA_CONSIDER_AWAY_INTERVAL,
    STORAGE_DATA_LOG_INCOMING_MESSAGES,
    STORAGE_DATA_MONITORED_DEVICES,
    STORAGE_DATA_MONITORED_INTERFACES,
    STORAGE_DATA_UPDATE_API_INTERVAL,
    STORAGE_DATA_UPDATE_ENTITIES_INTERVAL,
)
from ..models.config_data import ConfigData

_LOGGER = logging.getLogger(__name__)


class ConfigManager:
    _data: dict | None
    _config_data: ConfigData

    _store: Store | None
    _translations: dict | None
    _password: str | None
    _entry_title: str
    _entry_id: str

    _is_set_up_mode: bool
    _is_initialized: bool

    def __init__(self, hass: HomeAssistant | None, entry: ConfigEntry | None = None):
        self._hass = hass
        self._entry = entry
        self._entry_id = None if entry is None else entry.entry_id
        self._entry_title = DEFAULT_NAME if entry is None else entry.title

        self._config_data = ConfigData()

        self._data = None

        self._store = None
        self._translations = None

        self._is_set_up_mode = entry is None
        self._is_initialized = False

        if hass is not None:
            self._store = Store(
                hass, STORAGE_VERSION, CONFIGURATION_FILE, encoder=JSONEncoder
            )

    @property
    def is_initialized(self) -> bool:
        is_initialized = self._is_initialized

        return is_initialized

    @property
    def entry_id(self) -> str:
        entry_id = self._entry_id

        return entry_id

    @property
    def entry_title(self) -> str:
        entry_title = self._entry_title

        return entry_title

    @property
    def entry(self) -> ConfigEntry:
        entry = self._entry

        return entry

    @property
    def monitored_interfaces(self):
        result = self._data.get(STORAGE_DATA_MONITORED_INTERFACES, {})

        return result

    @property
    def monitored_devices(self):
        result = self._data.get(STORAGE_DATA_MONITORED_DEVICES, {})

        return result

    @property
    def log_incoming_messages(self):
        result = self._data.get(STORAGE_DATA_LOG_INCOMING_MESSAGES, False)

        return result

    @property
    def consider_away_interval(self):
        result = self._data.get(
            STORAGE_DATA_CONSIDER_AWAY_INTERVAL,
            DEFAULT_CONSIDER_AWAY_INTERVAL.total_seconds(),
        )

        return result

    @property
    def update_entities_interval(self):
        result = self._data.get(
            STORAGE_DATA_UPDATE_ENTITIES_INTERVAL,
            DEFAULT_UPDATE_ENTITIES_INTERVAL.total_seconds(),
        )

        return result

    @property
    def update_api_interval(self):
        result = self._data.get(
            STORAGE_DATA_UPDATE_API_INTERVAL,
            DEFAULT_UPDATE_API_INTERVAL.total_seconds(),
        )

        return result

    @property
    def config_data(self) -> ConfigData:
        config_data = self._config_data

        return config_data

    async def initialize(self, entry_config: dict):
        try:
            await self._load()

            self._config_data.update(entry_config)

            if self._hass is None:
                self._translations = {}

            else:
                self._translations = await translation.async_get_translations(
                    self._hass, self._hass.config.language, "entity", {DOMAIN}
                )

            _LOGGER.debug(
                f"Translations loaded, Data: {json.dumps(self._translations)}"
            )

            self._is_initialized = True

        except InvalidToken:
            self._is_initialized = False

            _LOGGER.error(
                f"Invalid encryption key, Please follow instructions in {INVALID_TOKEN_SECTION}"
            )

        except Exception as ex:
            self._is_initialized = False

            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(
                f"Failed to initialize configuration manager, Error: {ex}, Line: {line_number}"
            )

    def get_translation(
        self,
        platform: Platform,
        entity_key: str,
        attribute: str,
        default_value: str | None = None,
    ) -> str | None:
        translation_key = (
            f"component.{DOMAIN}.entity.{platform}.{entity_key}.{attribute}"
        )

        translated_value = self._translations.get(translation_key, default_value)

        _LOGGER.debug(
            "Translations requested, "
            f"Key: {translation_key}, "
            f"Default value: {default_value}, "
            f"Value: {translated_value}"
        )

        return translated_value

    def get_entity_name(
        self, key: str, name: str, device_name: str, platform: Platform
    ) -> str:
        entity_key = key

        translated_name = self.get_translation(platform, entity_key, CONF_NAME, name)

        entity_name = (
            device_name
            if translated_name is None or translated_name == ""
            else f"{device_name} {translated_name}"
        )

        return entity_name

    def get_debug_data(self) -> dict:
        data = self._config_data.to_dict()

        for key in self._data:
            data[key] = self._data[key]

        return data

    def get_monitored_interface(self, interface_name: str):
        _LOGGER.debug(f"Set monitored interface {interface_name}")

        is_enabled = self._data.get(STORAGE_DATA_MONITORED_INTERFACES, {}).get(
            interface_name, False
        )

        return is_enabled

    def get_monitored_device(self, device_mac: str):
        _LOGGER.debug(f"Get monitored device {device_mac}")

        is_enabled = self._data.get(STORAGE_DATA_MONITORED_DEVICES, {}).get(
            device_mac, False
        )

        return is_enabled

    async def _load(self):
        self._data = None

        await self._load_config_from_file()

        if self._data is None:
            self._data = {}

        default_configuration = self._get_defaults()

        for key in default_configuration:
            value = default_configuration[key]

            if key not in self._data:
                self._data[key] = value

        await self._save()

    @staticmethod
    def _get_defaults() -> dict:
        data = {
            STORAGE_DATA_MONITORED_INTERFACES: {},
            STORAGE_DATA_MONITORED_DEVICES: {},
            STORAGE_DATA_LOG_INCOMING_MESSAGES: False,
            STORAGE_DATA_CONSIDER_AWAY_INTERVAL: DEFAULT_CONSIDER_AWAY_INTERVAL.total_seconds(),
            STORAGE_DATA_UPDATE_ENTITIES_INTERVAL: DEFAULT_UPDATE_ENTITIES_INTERVAL.total_seconds(),
            STORAGE_DATA_UPDATE_API_INTERVAL: DEFAULT_UPDATE_API_INTERVAL.total_seconds(),
        }

        return data

    async def _load_config_from_file(self):
        if self._store is not None:
            store_data = await self._store.async_load()

            if store_data is not None:
                self._data = store_data.get(self._entry_id)

    async def remove(self, entry_id: str):
        if self._store is None:
            return

        store_data = await self._store.async_load()

        if store_data is not None and entry_id in store_data:
            data = {key: store_data[key] for key in store_data}
            data.pop(entry_id)

            await self._store.async_save(data)

    async def _save(self):
        if self._store is None:
            return

        should_save = False
        store_data = await self._store.async_load()

        if store_data is None:
            store_data = {}

        entry_data = store_data.get(self._entry_id, {})

        _LOGGER.debug(
            f"Storing config data: {json.dumps(self._data)}, "
            f"Exiting: {json.dumps(entry_data)}"
        )

        for key in self._data:
            stored_value = entry_data.get(key)

            if key in [CONF_PASSWORD, CONF_USERNAME]:
                entry_data.pop(key)

                if stored_value is not None:
                    should_save = True

            else:
                current_value = self._data.get(key)

                if stored_value != current_value:
                    should_save = True

                    entry_data[key] = self._data[key]

        if should_save and self._entry_id is not None:
            store_data[self._entry_id] = entry_data

            await self._store.async_save(store_data)

    async def set_monitored_interface(self, interface_name: str, is_enabled: bool):
        _LOGGER.debug(f"Set monitored interface {interface_name} to {is_enabled}")

        self._data[STORAGE_DATA_MONITORED_INTERFACES][interface_name] = is_enabled

        await self._save()

    async def set_monitored_device(self, device_mac: str, is_enabled: bool):
        _LOGGER.debug(f"Set monitored device {device_mac} to {is_enabled}")

        self._data[STORAGE_DATA_MONITORED_DEVICES][device_mac] = is_enabled

        await self._save()

    async def set_log_incoming_messages(self, enabled: bool):
        _LOGGER.debug(f"Set log incoming messages to {enabled}")

        self._data[STORAGE_DATA_LOG_INCOMING_MESSAGES] = enabled

        await self._save()

    async def set_consider_away_interval(self, interval: int):
        _LOGGER.debug(f"Changing {STORAGE_DATA_CONSIDER_AWAY_INTERVAL}: {interval}")

        self._data[STORAGE_DATA_CONSIDER_AWAY_INTERVAL] = interval

        await self._save()

    async def set_update_entities_interval(self, interval: int):
        _LOGGER.debug(f"Changing {STORAGE_DATA_UPDATE_ENTITIES_INTERVAL}: {interval}")

        self._data[STORAGE_DATA_UPDATE_ENTITIES_INTERVAL] = interval

        await self._save()

    async def set_update_api_interval(self, interval: int):
        _LOGGER.debug(f"Changing {STORAGE_DATA_UPDATE_API_INTERVAL}: {interval}")

        self._data[STORAGE_DATA_UPDATE_API_INTERVAL] = interval

        await self._save()
