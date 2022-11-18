"""
Core HA Manager.
"""
from __future__ import annotations

import datetime
import logging
import sys
from typing import Any

from cryptography.fernet import InvalidToken

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.entity_registry import EntityRegistry, async_get
from homeassistant.helpers.event import async_track_time_interval

from ..helpers.const import *
from ..managers.device_manager import DeviceManager
from ..managers.entity_manager import EntityManager
from ..managers.storage_manager import StorageManager
from ..models.entity_data import EntityData

_LOGGER = logging.getLogger(__name__)


class HomeAssistantManager:
    def __init__(self,
                 hass: HomeAssistant,
                 scan_interval: datetime.timedelta,
                 heartbeat_interval: datetime.timedelta | None = None
                 ):

        self._hass = hass

        self._is_initialized = False
        self._update_entities_interval = scan_interval
        self._update_data_providers_interval = scan_interval
        self._heartbeat_interval = heartbeat_interval

        self._entity_registry = None

        self._entry: ConfigEntry | None = None

        self._storage_manager = StorageManager(self._hass)
        self._entity_manager = EntityManager(self._hass, self)
        self._device_manager = DeviceManager(self._hass, self)

        self._entity_registry = async_get(self._hass)

        self._async_track_time_handlers = []
        self._last_heartbeat = None
        self._update_lock = False
        self._actions: dict = {}

        def _send_heartbeat(internal_now):
            self._last_heartbeat = internal_now

            self._hass.async_create_task(self.async_send_heartbeat())

        self._send_heartbeat = _send_heartbeat

        self._domains = {domain: self.is_domain_supported(domain) for domain in SUPPORTED_PLATFORMS}

    @property
    def entity_manager(self) -> EntityManager:
        if self._entity_manager is None:
            self._entity_manager = EntityManager(self._hass, self)

        return self._entity_manager

    @property
    def device_manager(self) -> DeviceManager:
        return self._device_manager

    @property
    def entity_registry(self) -> EntityRegistry:
        return self._entity_registry

    @property
    def storage_manager(self) -> StorageManager:
        return self._storage_manager

    @property
    def entry_id(self) -> str:
        return self._entry.entry_id

    @property
    def entry_title(self) -> str:
        return self._entry.title

    def update_intervals(self,
                         entities_interval: datetime.timedelta,
                         data_interval: datetime.timedelta
                         ):

        self._update_entities_interval = entities_interval
        self._update_data_providers_interval = data_interval

    async def async_component_initialize(self, entry: ConfigEntry):
        """ Component initialization """
        pass

    async def async_send_heartbeat(self):
        """ Must be implemented to be able to send heartbeat to API """
        pass

    def register_services(self, entry: ConfigEntry | None = None):
        """ Must be implemented to be able to expose services """
        pass

    async def async_initialize_data_providers(self):
        """ Must be implemented to be able to send heartbeat to API """
        pass

    async def async_stop_data_providers(self):
        """ Must be implemented to be able to send heartbeat to API """
        pass

    async def async_update_data_providers(self):
        """ Must be implemented to be able to send heartbeat to API """
        pass

    def load_entities(self):
        """ Must be implemented to be able to send heartbeat to API """
        pass

    def load_devices(self):
        """ Must be implemented to be able to send heartbeat to API """
        pass

    async def async_init(self, entry: ConfigEntry):
        try:
            self._entry = entry

            await self.async_component_initialize(entry)

            self._hass.loop.create_task(self._async_load_platforms())

        except InvalidToken:
            error_message = "Encryption key got corrupted, please remove the integration and re-add it"

            _LOGGER.error(error_message)

            data = await self._storage_manager.async_load_from_store()
            data.key = None

            await self._storage_manager.async_save_to_store(data)

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(f"Failed to async_init, error: {ex}, line: {line_number}")

    async def _async_load_platforms(self):
        load = self._hass.config_entries.async_forward_entry_setup

        for domain in self._domains:
            if self._domains.get(domain, False):
                await load(self._entry, domain)

            else:
                _LOGGER.debug(f"Skip loading {domain}")

        self.register_services()

        self._is_initialized = True

        await self.async_update_entry()

    def _update_data_providers(self, now):
        self._hass.async_create_task(self.async_update_data_providers())

    async def async_update_entry(self, entry: ConfigEntry | None = None):
        entry_changed = entry is not None

        if entry_changed:
            self._entry = entry

            _LOGGER.info(f"Handling ConfigEntry load: {entry.as_dict()}")

        else:
            entry = self._entry

            track_time_update_data_providers = async_track_time_interval(
                self._hass, self._update_data_providers, self._update_data_providers_interval
            )

            self._async_track_time_handlers.append(track_time_update_data_providers)

            track_time_update_entities = async_track_time_interval(
                self._hass, self._update_entities, self._update_entities_interval
            )

            self._async_track_time_handlers.append(track_time_update_entities)

            if self._heartbeat_interval is not None:
                track_time_send_heartbeat = async_track_time_interval(
                    self._hass, self._send_heartbeat, self._heartbeat_interval
                )

                self._async_track_time_handlers.append(track_time_send_heartbeat)

            _LOGGER.info(f"Handling ConfigEntry change: {entry.as_dict()}")

        await self.async_initialize_data_providers()

    async def async_unload(self):
        _LOGGER.info(f"HA was stopped")

        for handler in self._async_track_time_handlers:
            if handler is not None:
                handler()

        self._async_track_time_handlers.clear()

        await self.async_stop_data_providers()

    async def async_remove(self, entry: ConfigEntry):
        _LOGGER.info(f"Removing current integration - {entry.title}")

        await self.async_unload()

        unload = self._hass.config_entries.async_forward_entry_unload

        for domain in PLATFORMS:
            if self._domains.get(domain, False):
                await unload(self._entry, domain)

            else:
                _LOGGER.debug(f"Skip unloading {domain}")

        await self._device_manager.async_remove()

        self._entry = None
        self.entity_manager.entities.clear()

        _LOGGER.info(f"Current integration ({entry.title}) removed")

    def _update_entities(self, now):
        if self._update_lock:
            _LOGGER.warning("Update in progress, will skip the request")
            return

        self._update_lock = True

        try:
            self.load_devices()
            self.load_entities()

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(f"Failed to update devices and entities, Error: {ex}, Line: {line_number}")

        self.entity_manager.update()

        self._hass.async_create_task(self.dispatch_all())

        self._update_lock = False

    async def dispatch_all(self):
        if not self._is_initialized:
            _LOGGER.info("NOT INITIALIZED - Failed discovering components")
            return

        for domain in PLATFORMS:
            if self._domains.get(domain, False):
                signal = PLATFORMS.get(domain)

                async_dispatcher_send(self._hass, signal)

    def set_action(self, entity_id: str, action_name: str, action):
        key = f"{entity_id}:{action_name}"
        self._actions[key] = action

    def get_action(self, entity_id: str, action_name: str):
        key = f"{entity_id}:{action_name}"
        action = self._actions.get(key)

        return action

    def get_core_entity_fan_speed(self, entity: EntityData) -> str | None:
        pass

    async def async_core_entity_return_to_base(self, entity: EntityData) -> None:
        """ Handles ACTION_CORE_ENTITY_RETURN_TO_BASE. """
        action = self.get_action(entity.id, ACTION_CORE_ENTITY_RETURN_TO_BASE)

        if action is not None:
            await action(entity)

    async def async_core_entity_set_fan_speed(self, entity: EntityData, fan_speed: str) -> None:
        """ Handles ACTION_CORE_ENTITY_SET_FAN_SPEED. """
        action = self.get_action(entity.id, ACTION_CORE_ENTITY_SET_FAN_SPEED)

        if action is not None:
            await action(entity, fan_speed)

    async def async_core_entity_start(self, entity: EntityData) -> None:
        """ Handles ACTION_CORE_ENTITY_START. """
        action = self.get_action(entity.id, ACTION_CORE_ENTITY_START)

        if action is not None:
            await action(entity)

    async def async_core_entity_stop(self, entity: EntityData) -> None:
        """ Handles ACTION_CORE_ENTITY_STOP. """
        action = self.get_action(entity.id, ACTION_CORE_ENTITY_STOP)

        if action is not None:
            await action(entity)

    async def async_core_entity_pause(self, entity: EntityData) -> None:
        """ Handles ACTION_CORE_ENTITY_PAUSE. """
        action = self.get_action(entity.id, ACTION_CORE_ENTITY_PAUSE)

        if action is not None:
            await action(entity)

    async def async_core_entity_turn_on(self, entity: EntityData) -> None:
        """ Handles ACTION_CORE_ENTITY_TURN_ON. """
        action = self.get_action(entity.id, ACTION_CORE_ENTITY_TURN_ON)

        if action is not None:
            await action(entity)

    async def async_core_entity_turn_off(self, entity: EntityData) -> None:
        """ Handles ACTION_CORE_ENTITY_TURN_OFF. """
        action = self.get_action(entity.id, ACTION_CORE_ENTITY_TURN_OFF)

        if action is not None:
            await action(entity)

    async def async_core_entity_send_command(
            self,
            entity: EntityData,
            command: str,
            params: dict[str, Any] | list[Any] | None = None
    ) -> None:
        """ Handles ACTION_CORE_ENTITY_SEND_COMMAND. """
        action = self.get_action(entity.id, ACTION_CORE_ENTITY_SEND_COMMAND)

        if action is not None:
            await action(entity, command, params)

    async def async_core_entity_locate(self, entity: EntityData) -> None:
        """ Handles ACTION_CORE_ENTITY_LOCATE. """
        action = self.get_action(entity.id, ACTION_CORE_ENTITY_LOCATE)

        if action is not None:
            await action(entity)

    async def async_core_entity_select_option(self, entity: EntityData, option: str) -> None:
        """ Handles ACTION_CORE_ENTITY_SELECT_OPTION. """
        action = self.get_action(entity.id, ACTION_CORE_ENTITY_SELECT_OPTION)

        if action is not None:
            await action(entity, option)

    async def async_core_entity_toggle(self, entity: EntityData) -> None:
        """ Handles ACTION_CORE_ENTITY_TOGGLE. """
        action = self.get_action(entity.id, ACTION_CORE_ENTITY_TOGGLE)

        if action is not None:
            await action(entity)

    async def async_core_entity_enable_motion_detection(self, entity: EntityData) -> None:
        """ Handles ACTION_CORE_ENTITY_ENABLE_MOTION_DETECTION. """
        action = self.get_action(entity.id, ACTION_CORE_ENTITY_ENABLE_MOTION_DETECTION)

        if action is not None:
            await action(entity)

    async def async_core_entity_disable_motion_detection(self, entity: EntityData) -> None:
        """ Handles ACTION_CORE_ENTITY_DISABLE_MOTION_DETECTION. """
        action = self.get_action(entity.id, ACTION_CORE_ENTITY_DISABLE_MOTION_DETECTION)

        if action is not None:
            await action(entity)

    @staticmethod
    def log_exception(ex, message):
        exc_type, exc_obj, tb = sys.exc_info()
        line_number = tb.tb_lineno

        _LOGGER.error(f"{message}, Error: {str(ex)}, Line: {line_number}")

    @staticmethod
    def is_domain_supported(domain) -> bool:
        is_supported = True

        try:
            __import__(f"custom_components.{DOMAIN}.{domain}")
        except ModuleNotFoundError as mnfe:
            is_supported = False

        return is_supported
