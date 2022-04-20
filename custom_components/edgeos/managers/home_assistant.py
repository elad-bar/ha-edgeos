"""
This component provides support for Home Automation Manager (HAM).
For more details about this component, please refer to the documentation at
https://home-assistant.io/components/edgeos/
"""
import logging
import sys
from typing import Optional

from cryptography.fernet import InvalidToken

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.entity_registry import EntityRegistry, async_get_registry
from homeassistant.helpers.event import async_track_time_interval

from ..helpers.const import *
from ..models.config_data import ConfigData
from .configuration_manager import ConfigManager
from .data_manager import EdgeOSData
from .device_manager import DeviceManager
from .entity_manager import EntityManager
from .password_manager import PasswordManager
from .storage_manager import StorageManager

_LOGGER = logging.getLogger(__name__)


class EdgeOSHomeAssistant:
    def __init__(self, hass: HomeAssistant, password_manager: PasswordManager):
        self._hass = hass

        self._remove_async_track_timers = {}

        self._is_first_time_online = True
        self._is_initialized = False
        self._is_ready = False

        self._entity_registry = None
        self._data_manager = None
        self._device_manager = None
        self._entity_manager = None
        self._storage_manager = None

        self._config_manager = ConfigManager(password_manager)

        def update_api(internal_now):
            self._hass.async_create_task(self.async_update_api(internal_now))

        def update_entities(internal_now):
            self._hass.async_create_task(self.async_update_entities(internal_now))

        def send_heartbeat(internal_now):
            self._hass.async_create_task(self.async_send_heartbeat(internal_now))

        self._send_heartbeat = send_heartbeat
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

    def set_async_track_timer(self, key, interval, callback):
        timer = self._remove_async_track_timers.get(key)

        if timer is not None:
            previous_interval = timer.get("interval")

            if previous_interval != interval:
                _LOGGER.info(
                    f"Updating {key} timer interval from {previous_interval}s to {interval}s"
                )

                self.remove_async_track_timer(key, False)
            else:
                return
        else:
            _LOGGER.info(f"Adding {key} timer, interval: {interval}s")

        new_handler = async_track_time_interval(
            self._hass, callback, timedelta(seconds=interval)
        )

        self._remove_async_track_timers[key] = {
            "interval": interval,
            "handler": new_handler,
        }

    def remove_async_track_timer(self, key, log=True):
        timer = self._remove_async_track_timers.get(key)

        if timer is not None:
            if log:
                _LOGGER.info(f"Removing {key} timer")

            handler = timer.get("handler")

            if handler is not None:
                handler()

                self._remove_async_track_timers[key]["handler"] = None

            self._remove_async_track_timers[key] = None
        else:
            _LOGGER.warning(f"{key} timer was not found, cannot remove")

    async def async_init(self, entry: ConfigEntry):
        try:
            self._storage_manager = StorageManager(self._hass)

            await self._config_manager.update(entry)

            self._data_manager = EdgeOSData(
                self._hass, self._config_manager, self.update
            )

            self._device_manager = DeviceManager(self._hass, self)
            self._entity_manager = EntityManager(self._hass, self)

            self._hass.loop.create_task(self.initialize())
        except InvalidToken:
            error_message = "Encryption key got corrupted, please remove the integration and re-add it"

            _LOGGER.error(error_message)

            data = await self._storage_manager.async_load_from_store()
            data.key = None
            await self._storage_manager.async_save_to_store(data)

            await self._hass.services.async_call(
                "persistent_notification",
                "create",
                {"title": DEFAULT_NAME, "message": error_message},
            )

    async def initialize(self):
        self._entity_registry = await async_get_registry(self._hass)

        load = self._hass.config_entries.async_forward_entry_setup

        for domain in SIGNALS:
            await load(self._config_manager.config_entry, domain)

        self.register_service_generate_debug_file()

        self._is_initialized = True

        await self._data_manager.initialize(self.async_update_entry)

    async def async_remove(self, entry: ConfigEntry):
        _LOGGER.info(f"Removing {entry.title}")

        await self._data_manager.terminate()

        for timer_key in self._remove_async_track_timers:
            self.remove_async_track_timer(timer_key)

        unload = self._hass.config_entries.async_forward_entry_unload
        for domain in SIGNALS:
            await unload(entry, domain)

        await self._device_manager.async_remove_entry(entry.entry_id)

        _LOGGER.info(f"{entry.title} removed")

    async def async_update_entry(self, entry: ConfigEntry = None):
        is_update = entry is not None

        if not is_update:
            entry = self._config_manager.config_entry

        _LOGGER.info(f"Handling ConfigEntry change: {entry.as_dict()}")

        await self._config_manager.update(entry)

        await self.async_update_api(datetime.now())

        await self.discover_all()

        config = self.config_data

        self.set_async_track_timer(
            "Entities", config.update_entities_interval, self._update_entities
        )
        self.set_async_track_timer("API", config.update_api_interval, self._update_api)
        self.set_async_track_timer(
            "Heartbeat", HEARTBEAT_INTERVAL_SECONDS, self._send_heartbeat
        )

        self._is_ready = False

    async def async_send_heartbeat(self, event_time):
        if not self._is_initialized:
            _LOGGER.info(f"NOT INITIALIZED, cannot perform heartbeat: {event_time}")

            return

        await self._data_manager.async_send_heartbeat()

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

        await self.discover_all()

    def register_service_generate_debug_file(self):
        self._hass.services.async_register(DOMAIN, GENERATE_DEBUG_FILE, self.async_service_generate_debug_file)

    async def async_service_generate_debug_file(self, call_service):
        await self._storage_manager.async_save_debug_to_store(self.data_manager.system_data)

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
