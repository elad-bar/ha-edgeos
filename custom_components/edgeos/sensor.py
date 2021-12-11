"""
Support for EdgeOS binary sensors.
For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/binary_sensor.edgeos/
"""
import logging

from custom_components.edgeos.helpers.const import *
from custom_components.edgeos.models.base_entity import (
    EdgeOSEntity,
    async_setup_base_entry,
)
from custom_components.edgeos.models.entity_data import EntityData
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

CURRENT_DOMAIN = DOMAIN_SENSOR


def get_device_tracker(hass: HomeAssistant, integration_name: str, entity: EntityData):
    sensor = EdgeOSSensor()
    sensor.initialize(hass, integration_name, entity, CURRENT_DOMAIN)

    return sensor


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities):
    """Set up EdgeOS based off an entry."""
    await async_setup_base_entry(
        hass, entry, async_add_entities, CURRENT_DOMAIN, get_device_tracker
    )


async def async_unload_entry(hass, config_entry):
    _LOGGER.info(f"async_unload_entry {CURRENT_DOMAIN}: {config_entry}")

    return True


class EdgeOSSensor(EdgeOSEntity):
    """Representation a binary sensor that is updated by EdgeOS."""

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self.entity.state

    async def async_added_to_hass_local(self):
        _LOGGER.info(f"Added new {self.name}")

    @property
    def device_class(self) -> SensorDeviceClass:
        """Return the class of this sensor."""
        return self.entity.sensor_device_class

    def _immediate_update(self, previous_state: bool):
        if previous_state != self.entity.state:
            _LOGGER.debug(
                f"{self.name} updated from {previous_state} to {self.entity.state}"
            )

        super()._immediate_update(previous_state)
