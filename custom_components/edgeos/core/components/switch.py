"""
Support for switch.
"""
from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant

from ..helpers.const import DOMAIN_SWITCH
from ..models.base_entity import BaseEntity
from ..models.entity_data import EntityData


class CoreSwitch(SwitchEntity, BaseEntity):
    """Class for a  switch."""

    @property
    def is_on(self) -> bool | None:
        """Return the boolean response if the node is on."""
        return self.entity.state

    def turn_on(self, **kwargs: Any) -> None:
        self.hass.async_create_task(self.async_turn_on())

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.ha.async_core_entity_turn_on(self.entity)

    def turn_off(self, **kwargs: Any) -> None:
        self.hass.async_create_task(self.async_turn_off())

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.ha.async_core_entity_turn_off(self.entity)

    async def async_setup(self):
        pass

    @staticmethod
    def get_component(hass: HomeAssistant, entity: EntityData):
        switch = CoreSwitch()
        switch.initialize(hass, entity, DOMAIN_SWITCH)

        return switch

    @staticmethod
    def get_domain():
        return DOMAIN_SWITCH
