from abc import ABC
import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ICON, Platform
from homeassistant.core import HomeAssistant

from .common.base_entity import IntegrationBaseEntity, async_setup_base_entry
from .common.consts import (
    ACTION_ENTITY_TURN_OFF,
    ACTION_ENTITY_TURN_ON,
    ATTR_ATTRIBUTES,
    ATTR_IS_ON,
)
from .common.entity_descriptions import IntegrationSwitchEntityDescription
from .common.enums import DeviceTypes
from .managers.coordinator import Coordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
):
    await async_setup_base_entry(
        hass,
        entry,
        Platform.SWITCH,
        IntegrationSwitchEntity,
        async_add_entities,
    )


class IntegrationSwitchEntity(IntegrationBaseEntity, SwitchEntity, ABC):
    """Representation of a sensor."""

    def __init__(
        self,
        hass: HomeAssistant,
        entity_description: IntegrationSwitchEntityDescription,
        coordinator: Coordinator,
        device_type: DeviceTypes,
        item_id: str | None,
    ):
        super().__init__(hass, entity_description, coordinator, device_type, item_id)

        self._attr_device_class = entity_description.device_class

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the entity on."""
        await self.async_execute_device_action(ACTION_ENTITY_TURN_ON)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the entity off."""
        await self.async_execute_device_action(ACTION_ENTITY_TURN_OFF)

    def update_component(self, data):
        """Fetch new state parameters for the sensor."""
        if data is not None:
            is_on = data.get(ATTR_IS_ON)
            attributes = data.get(ATTR_ATTRIBUTES)
            icon = data.get(ATTR_ICON)

            self._attr_is_on = is_on
            self._attr_extra_state_attributes = attributes

            if icon is not None:
                self._attr_icon = icon

        else:
            self._attr_is_on = None
