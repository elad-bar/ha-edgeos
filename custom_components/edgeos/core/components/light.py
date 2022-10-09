"""
Support for light.
"""
from __future__ import annotations

from abc import ABC
import logging
from typing import Any

from homeassistant.components.light import ColorMode, LightEntity
from homeassistant.core import HomeAssistant

from ..helpers.const import *
from ..models.base_entity import BaseEntity
from ..models.entity_data import EntityData

_LOGGER = logging.getLogger(__name__)


class CoreLight(LightEntity, BaseEntity, ABC):
    """Class for a light."""

    @property
    def is_on(self) -> bool | None:
        """Return the boolean response if the node is on."""
        return self.entity.state

    @property
    def supported_color_modes(self) -> set[ColorMode] | set[str] | None:
        """Flag supported color modes."""
        return set(ColorMode.ONOFF)

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.ha.async_core_entity_turn_on(self.entity)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.ha.async_core_entity_turn_off(self.entity)

    async def async_setup(self):
        pass

    @staticmethod
    def get_component(hass: HomeAssistant, entity: EntityData):
        switch = CoreLight()
        switch.initialize(hass, entity, DOMAIN_LIGHT)

        return switch

    @staticmethod
    def get_domain():
        return DOMAIN_LIGHT
