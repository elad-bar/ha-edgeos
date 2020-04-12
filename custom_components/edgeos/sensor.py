"""
Support for EdgeOS binary sensors.
For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/binary_sensor.edgeos/
"""
import logging
from typing import Union

from .base_entity import EdgeOSEntity, _async_setup_entry
from .const import *

_LOGGER = logging.getLogger(__name__)

CURRENT_DOMAIN = DOMAIN_SENSOR


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up EdgeOS based off an entry."""
    await _async_setup_entry(hass, entry, async_add_entities, CURRENT_DOMAIN, EdgeOSSensor)


async def async_unload_entry(hass, config_entry):
    _LOGGER.info(f"async_unload_entry {CURRENT_DOMAIN}: {config_entry}")

    return True


class EdgeOSSensor(EdgeOSEntity):
    """Representation a binary sensor that is updated by EdgeOS."""

    def __init__(self, hass, ha, entity):
        """Initialize the EdgeOS Sensor."""
        super().__init__(hass, ha, entity, CURRENT_DOMAIN)

    @property
    def state(self) -> Union[None, str, int, float]:
        """Return the state of the sensor."""
        return self._entity.get(ENTITY_STATE)
