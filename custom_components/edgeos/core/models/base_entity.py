from __future__ import annotations

import logging
import sys

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity

from ..helpers.const import *
from ..managers.device_manager import DeviceManager
from ..managers.entity_manager import EntityManager
from ..models.entity_data import EntityData

_LOGGER = logging.getLogger(__name__)


class BaseEntity(Entity):
    """Representation a base entity."""

    hass: HomeAssistant | None = None
    entity: EntityData | None = None
    remove_dispatcher = None
    current_domain: str = None

    ha = None
    entity_manager: EntityManager = None
    device_manager: DeviceManager = None

    def initialize(
        self,
        hass: HomeAssistant,
        entity: EntityData,
        current_domain: str,
    ):
        try:
            self.hass = hass
            self.entity = entity
            self.remove_dispatcher = None
            self.current_domain = current_domain

            ha_data = hass.data.get(DATA, dict())

            self.ha = ha_data.get(entity.entry_id)

            if self.ha is None:
                _LOGGER.warning("Failed to initialize BaseEntity without HA manager")
                return

            self.entity_manager = self.ha.entity_manager
            self.device_manager = self.ha.device_manager
            self.entity_description = entity.entity_description

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(f"Failed to initialize BaseEntity, Error: {ex}, Line: {line_number}")

    @property
    def entry_id(self) -> str | None:
        """Return the name of the node."""
        return self.entity.entry_id

    @property
    def unique_id(self) -> str | None:
        """Return the name of the node."""
        return self.entity.id

    @property
    def device_info(self):
        return self.device_manager.get(self.entity.device_name)

    @property
    def name(self):
        """Return the name of the node."""
        return self.entity.name

    @property
    def extra_state_attributes(self):
        """Return true if the binary sensor is on."""
        return self.entity.attributes

    async def async_added_to_hass(self):
        """Register callbacks."""
        async_dispatcher_connect(
            self.hass, PLATFORMS[self.current_domain], self._schedule_immediate_update
        )

        await self.async_added_to_hass_local()

    async def async_will_remove_from_hass(self) -> None:
        if self.remove_dispatcher is not None:
            self.remove_dispatcher()
            self.remove_dispatcher = None

        _LOGGER.debug(f"Removing component: {self.unique_id}")

        self.entity = None

        await self.async_will_remove_from_hass_local()

    @callback
    def _schedule_immediate_update(self):
        self.hass.async_create_task(self._async_schedule_immediate_update())

    async def _async_schedule_immediate_update(self):
        if self.entity_manager is None:
            _LOGGER.debug(
                f"Cannot update {self.current_domain} - Entity Manager is None | {self.name}"
            )
        else:
            if self.entity is not None:
                entity = self.entity_manager.get(self.unique_id)

                if entity is None:
                    _LOGGER.debug(f"Skip updating {self.name}, Entity is None")

                elif entity.disabled:
                    _LOGGER.debug(f"Skip updating {self.name}, Entity is disabled")

                else:
                    self.entity = entity
                    if self.entity is not None:
                        self.async_schedule_update_ha_state(True)

    async def async_added_to_hass_local(self):
        pass

    async def async_will_remove_from_hass_local(self):
        pass
