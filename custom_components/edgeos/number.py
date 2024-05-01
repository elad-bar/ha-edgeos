from abc import ABC
import logging

from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_STATE, Platform
from homeassistant.core import HomeAssistant

from .common.base_entity import IntegrationBaseEntity, async_setup_base_entry
from .common.consts import ACTION_ENTITY_SET_NATIVE_VALUE, ATTR_ATTRIBUTES
from .common.entity_descriptions import IntegrationNumberEntityDescription
from .managers.coordinator import Coordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
):
    await async_setup_base_entry(
        hass,
        entry,
        Platform.NUMBER,
        IntegrationNumberEntity,
        async_add_entities,
    )


class IntegrationNumberEntity(IntegrationBaseEntity, NumberEntity, ABC):
    """Representation of a sensor."""

    def __init__(
        self,
        hass: HomeAssistant,
        entity_description: IntegrationNumberEntityDescription,
        coordinator: Coordinator,
        item_id: str | None,
    ):
        super().__init__(hass, entity_description, coordinator, item_id)

        self.entity_description = entity_description

        self._attr_native_min_value = entity_description.native_min_value
        self._attr_native_max_value = entity_description.native_max_value
        self._attr_native_step = 1

    async def async_set_native_value(self, value: float) -> None:
        """Change the selected option."""
        await self.async_execute_device_action(
            ACTION_ENTITY_SET_NATIVE_VALUE, int(value)
        )

    def update_component(self, data):
        """Fetch new state parameters for the sensor."""
        if data is not None:
            state = data.get(ATTR_STATE)
            attributes = data.get(ATTR_ATTRIBUTES)

            self._attr_native_value = int(state)
            self._attr_extra_state_attributes = attributes

        else:
            self._attr_native_value = None
