"""
Support for EdgeOS binary sensors.
For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/binary_sensor.edgeos/
"""
import sys
import logging
from typing import Union

from .base_entity import EdgeOSEntity, _get_ha
from .const import *

_LOGGER = logging.getLogger(__name__)

CURRENT_DOMAIN = DOMAIN_SENSOR


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up EdgeOS based off an entry."""
    _LOGGER.debug(f"Starting async_setup_entry {CURRENT_DOMAIN}")

    try:
        entry_data = entry.data
        name = entry_data.get(CONF_NAME)

        ha = _get_ha(hass, name)
        entity_manager = ha.entity_manager
        entity_manager.set_domain_component(CURRENT_DOMAIN, async_add_entities, EdgeOSSensor)
    except Exception as ex:
        exc_type, exc_obj, tb = sys.exc_info()
        line_number = tb.tb_lineno

        _LOGGER.error(f"Failed to load {CURRENT_DOMAIN}, error: {ex}, line: {line_number}")


async def async_unload_entry(hass, config_entry):
    _LOGGER.info(f"async_unload_entry {CURRENT_DOMAIN}: {config_entry}")

    entry_data = config_entry.data
    name = entry_data.get(CONF_NAME)

    ha = _get_ha(hass, name)
    entity_manager = ha.entity_manager

    if entity_manager is not None:
        entity_manager.set_entry_loaded_state(CURRENT_DOMAIN, False)

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
