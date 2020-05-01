"""
This component provides support for Home Automation Manager (HAM).
For more details about this component, please refer to the documentation at
https://home-assistant.io/components/edgeos/
"""
import logging
import sys
from typing import Optional

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.entity_registry import EntityRegistry, async_get_registry
from homeassistant.helpers.event import async_call_later, async_track_time_interval

from ..helpers.const import *
from ..models.config_data import ConfigData
from .configuration_manager import ConfigManager
from .data_manager import EdgeOSData
from .device_manager import DeviceManager
from .entity_manager import EntityManager
from .password_manager import PasswordManager

_LOGGER = logging.getLogger(__name__)


class EdgeOSHomeAssistant:
    def __init__(self, hass: HomeAssistant, password_manager: PasswordManager):
        self._hass = hass

        self._remove_async_track_time_api = None
        self._remove_async_track_time_entities = None

        self._is_first_time_online = True
        self._is_initialized = False
        self._is_ready = False

        self._entity_registry = None
        self._data_manager = None
        self._device_manager = None
        self._entity_manager = None

        self._config_manager = ConfigManager(password_manager)

        def update_api(internal_now):
            self._hass.async_create_task(self.async_update_api(internal_now))

        def update_entities(internal_now):
            self._hass.async_create_task(self.async_update_entities(internal_now))

        self._update_api = update_api
        self._update_entities = update_entities

    @property
    def config_manager(self) -> ConfigManager:
        return self._config_manager

    @property
    def config_data(self) -> Optional[ConfigData]:
        if self._config_manager is not None:
            return self._config_manager.data

        return None

    @property
    def data_manager(self) -> EdgeOSData:
        return self._data_manager

    @property
    def entity_manager(self) -> EntityManager:
        return self._entity_manager

    @property
    def device_manager(self) -> DeviceManager:
        return self._device_manager

    @property
    def entity_registry(self) -> EntityRegistry:
        return self._entity_registry

    async def async_init(self, entry: ConfigEntry):
        self._config_manager.update(entry)

        self._data_manager = EdgeOSData(self._hass, self._config_manager, self.update)
        self._device_manager = DeviceManager(self._hass, self)
        self._entity_manager = EntityManager(self._hass, self)

        def internal_async_init(now):
            self._hass.async_create_task(self._async_init(now))

        self._entity_registry = await async_get_registry(self._hass)

        async_call_later(self._hass, 2, internal_async_init)

    async def _async_init(self, now):
        _LOGGER.debug(f"Initializing EdgeOS @{now}")

        load = self._hass.config_entries.async_forward_entry_setup

        for domain in SIGNALS:
            self._hass.async_create_task(
                load(self._config_manager.config_entry, domain)
            )

        self._hass.async_create_task(
            self._data_manager.initialize(self.async_post_initial_login)
        )

        self._is_initialized = True

    async def async_post_initial_login(self):
        _LOGGER.debug("Post initial login action")

        self._hass.async_create_task(self.async_update_api(datetime.now()))

        self._remove_async_track_time_api = async_track_time_interval(
            self._hass, self._update_api, SCAN_INTERVAL_API
        )

        await self.async_update_entry()

    async def async_remove(self):
        _LOGGER.debug(f"async_remove called")

        await self._data_manager.terminate()

        if self._remove_async_track_time_api is not None:
            self._remove_async_track_time_api()
            self._remove_async_track_time_api = None

        if self._remove_async_track_time_entities is not None:
            self._remove_async_track_time_entities()
            self._remove_async_track_time_entities = None

        unload = self._hass.config_entries.async_forward_entry_unload

        for domain in SIGNALS:
            self._hass.async_create_task(
                unload(self._config_manager.config_entry, domain)
            )

        await self._device_manager.async_remove_entry(
            self._config_manager.config_entry.entry_id
        )

    async def async_update_entry(self, entry: ConfigEntry = None):
        is_update = entry is not None

        if not is_update:
            entry = self._config_manager.config_entry

        _LOGGER.info(f"Handling ConfigEntry change: {entry.as_dict()}")

        if is_update:
            previous_interval = self.config_data.update_interval

            self._config_manager.update(entry)

            is_interval_changed = previous_interval != self.config_data.update_interval

            if (
                is_interval_changed
                and self._remove_async_track_time_entities is not None
            ):
                msg = f"ConfigEntry interval changed from {previous_interval} to {self.config_data.update_interval}"
                _LOGGER.info(msg)

                self._remove_async_track_time_entities()
                self._remove_async_track_time_entities = None

        if self._remove_async_track_time_entities is None:
            interval = timedelta(seconds=self.config_data.update_interval)

            self._remove_async_track_time_entities = async_track_time_interval(
                self._hass, self._update_entities, interval
            )

        self._is_ready = False

        self._data_manager.update(True)

        await self.discover_all()

    async def async_update_api(self, event_time):
        if not self._is_initialized:
            _LOGGER.info(f"NOT INITIALIZED, cannot update data from API: {event_time}")

            return

        _LOGGER.debug(f"Update API: {event_time}")

        await self._data_manager.refresh()

    async def async_update_entities(self, event_time):
        if not self._is_initialized:
            _LOGGER.info(f"NOT INITIALIZED, cannot update entities: {event_time}")

            return

        if self._is_first_time_online:
            self._is_first_time_online = False

            await self.async_update_api(datetime.now())

        await self.discover_all()

    def update(self):
        try:
            default_device_info = self.device_manager.get(DEFAULT_NAME)

            if CONF_NAME in default_device_info:
                self.entity_manager.update()

            self._is_ready = True
        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(f"Failed to update, Error: {ex}, Line: {line_number}")

    async def discover_all(self):
        if not self._is_ready or not self._is_initialized:
            return

        _LOGGER.debug(f"discover_all started")

        self.device_manager.update()

        default_device_info = self.device_manager.get(DEFAULT_NAME)

        if CONF_NAME in default_device_info:
            for domain in SIGNALS:
                signal = SIGNALS.get(domain)

                async_dispatcher_send(self._hass, signal)

    async def delete_entity(self, domain, name):
        try:
            entity = self.entity_manager.get_entity(domain, name)
            device_name = entity.device_name
            unique_id = entity.unique_id

            self.entity_manager.delete_entity(domain, name)

            device_in_use = self.entity_manager.is_device_name_in_use(device_name)

            entity_id = self.entity_registry.async_get_entity_id(
                domain, DOMAIN, unique_id
            )
            self.entity_registry.async_remove(entity_id)

            if not device_in_use:
                await self.device_manager.delete_device(device_name)
        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(f"Failed to delete_entity, Error: {ex}, Line: {line_number}")

    def service_save_debug_data(self):
        _LOGGER.debug(f"Save Debug Data")

        try:
            path = self._hass.config.path(EDGEOS_DATA_LOG)

            with open(path, "w+") as out:
                out.write(str(self.data_manager.edgeos_data))

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(
                f"Failed to log EdgeOS data, Error: {ex}, Line: {line_number}"
            )
