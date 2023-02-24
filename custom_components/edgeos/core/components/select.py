"""
Support for select.
"""
from __future__ import annotations

from abc import ABC
import logging
import sys

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant

from ..helpers.const import ATTR_OPTIONS, DOMAIN_SELECT
from ..models.base_entity import BaseEntity
from ..models.entity_data import EntityData

_LOGGER = logging.getLogger(__name__)


class CoreSelect(SelectEntity, BaseEntity, ABC):
    """Core Select"""

    def initialize(
        self,
        hass: HomeAssistant,
        entity: EntityData,
        current_domain: str,
    ):
        super().initialize(hass, entity, current_domain)

        try:
            if hasattr(self.entity_description, ATTR_OPTIONS):
                self._attr_options = getattr(self.entity_description, ATTR_OPTIONS)

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(
                f"Failed to initialize CoreSelect instance, Error: {ex}, Line: {line_number}"
            )

    @property
    def current_option(self) -> str:
        """Return current lamp mode."""
        return str(self.entity.state)

    async def async_select_option(self, option: str) -> None:
        """Select option."""
        await self.ha.async_core_entity_select_option(self.entity, option)

    @staticmethod
    def get_component(hass: HomeAssistant, entity: EntityData):
        select = CoreSelect()
        select.initialize(hass, entity, DOMAIN_SELECT)

        return select

    @staticmethod
    def get_domain():
        return DOMAIN_SELECT
