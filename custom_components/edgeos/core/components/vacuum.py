from __future__ import annotations

from abc import ABC
import logging
import sys
from typing import Any

from homeassistant.components.vacuum import StateVacuumEntity
from homeassistant.core import HomeAssistant

from ..helpers.const import *
from ..models.base_entity import BaseEntity
from ..models.entity_data import EntityData

_LOGGER = logging.getLogger(__name__)


class CoreVacuum(StateVacuumEntity, BaseEntity, ABC):
    """Class for a Shinobi Video switch."""

    def initialize(
        self,
        hass: HomeAssistant,
        entity: EntityData,
        current_domain: str,
    ):
        super().initialize(hass, entity, current_domain)

        try:
            if hasattr(self.entity_description, ATTR_FEATURES):
                self._attr_supported_features = getattr(self.entity_description, ATTR_FEATURES)

            if hasattr(self.entity_description, ATTR_FANS_SPEED_LIST):
                self._attr_fan_speed_list = getattr(self.entity_description, ATTR_FANS_SPEED_LIST)

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(f"Failed to initialize CoreSelect instance, Error: {ex}, Line: {line_number}")

    @property
    def state(self) -> str | None:
        """Return the status of the vacuum cleaner."""
        return self.entity.state

    @property
    def fan_speed(self) -> str | None:
        """Return the fan speed of the vacuum cleaner."""
        return self.ha.get_core_entity_fan_speed(self.entity)

    async def async_return_to_base(self, **kwargs: Any) -> None:
        """Set the vacuum cleaner to return to the dock."""
        await self.ha.async_core_entity_return_to_base(self.entity)

    async def async_set_fan_speed(self, fan_speed: str, **kwargs: Any) -> None:
        await self.ha.async_core_entity_set_fan_speed(self.entity, fan_speed)

    async def async_start(self, **kwargs: Any) -> None:
        await self.ha.async_core_entity_start(self.entity)

    async def async_stop(self, **kwargs: Any) -> None:
        await self.ha.async_core_entity_stop(self.entity)

    async def async_pause(self, **kwargs: Any) -> None:
        await self.ha.async_core_entity_pause(self.entity)

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.ha.async_core_entity_turn_on(self.entity)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.ha.async_core_entity_turn_off(self.entity)

    async def async_toggle(self, **kwargs: Any) -> None:
        await self.ha.async_core_entity_toggle(self.entity)

    async def async_send_command(
            self,
            command: str,
            params: dict[str, Any] | list[Any] | None = None,
            **kwargs: Any,
    ) -> None:
        """Send a command to a vacuum cleaner."""
        await self.ha.async_core_entity_send_command(self.entity, command, params)

    async def async_locate(self, **kwargs: Any) -> None:
        """Locate the vacuum cleaner."""
        await self.ha.async_core_entity_locate(self.entity)

    @staticmethod
    def get_component(hass: HomeAssistant, entity: EntityData):
        vacuum = CoreVacuum()
        vacuum.initialize(hass, entity, DOMAIN_VACUUM)

        return vacuum

    @staticmethod
    def get_domain():
        return DOMAIN_VACUUM
