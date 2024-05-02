import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ICON, ATTR_STATE, Platform
from homeassistant.core import HomeAssistant

from .common.base_entity import IntegrationBaseEntity, async_setup_base_entry
from .common.consts import ATTR_ATTRIBUTES
from .common.entity_descriptions import IntegrationSensorEntityDescription
from .common.enums import DeviceTypes
from .managers.coordinator import Coordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
):
    await async_setup_base_entry(
        hass,
        entry,
        Platform.SENSOR,
        IntegrationSensorEntity,
        async_add_entities,
    )


class IntegrationSensorEntity(IntegrationBaseEntity, SensorEntity):
    """Representation of a sensor."""

    def __init__(
        self,
        hass: HomeAssistant,
        entity_description: IntegrationSensorEntityDescription,
        coordinator: Coordinator,
        device_type: DeviceTypes,
        item_id: str | None,
    ):
        super().__init__(hass, entity_description, coordinator, device_type, item_id)

        self._attr_device_class = entity_description.device_class

    def update_component(self, data):
        """Fetch new state parameters for the sensor."""
        if data is not None:
            state = data.get(ATTR_STATE)
            attributes = data.get(ATTR_ATTRIBUTES)
            icon = data.get(ATTR_ICON)

            self._attr_native_value = state
            self._attr_extra_state_attributes = attributes

            if icon is not None:
                self._attr_icon = icon

        else:
            self._attr_native_value = None
