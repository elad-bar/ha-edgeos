"""
Support for EdgeOS binary sensors.
For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/binary_sensor.edgeos/
"""
import sys
import logging

from homeassistant.const import STATE_ON, STATE_OFF

from .base_entity import EdgeOSEntity, _get_ha
from .const import *

_LOGGER = logging.getLogger(__name__)

CURRENT_DOMAIN = DOMAIN_BINARY_SENSOR


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up EdgeOS based off an entry."""
    _LOGGER.debug(f"Starting async_setup_entry {CURRENT_DOMAIN}")

    try:
        entry_data = entry.data
        name = entry_data.get(CONF_NAME)

        ha = _get_ha(hass, name)
        entity_manager = ha.entity_manager
        entity_manager.set_domain_component(CURRENT_DOMAIN, async_add_entities, EdgeOSBinarySensor)
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


class EdgeOSBinarySensor(EdgeOSEntity):
    """Representation a binary sensor that is updated by EdgeOS."""

    def __init__(self, hass, ha, entity):
        """Initialize the EdgeOS Binary Sensor."""
        super().__init__(hass, ha, entity, CURRENT_DOMAIN)

    @property
    def is_on(self):
        """Return true if the binary sensor is on."""
        return bool(self._entity.get(ENTITY_STATE, False))

    @property
    def state(self):
        """Return the state of the binary sensor."""
        return STATE_ON if self.is_on else STATE_OFF
