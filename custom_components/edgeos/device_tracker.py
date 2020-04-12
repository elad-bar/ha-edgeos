"""
Support for Ubiquiti EdgeOS routers.
HEAVILY based on the AsusWRT component
For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/device_tracker.edgeos/
"""
import logging

from homeassistant.components.device_tracker import ATTR_SOURCE_TYPE, SOURCE_TYPE_ROUTER
from homeassistant.components.device_tracker.config_entry import ScannerEntity

from .base_entity import EdgeOSEntity, _async_setup_entry
from .const import *

_LOGGER = logging.getLogger(__name__)
DEPENDENCIES = [DOMAIN]

CURRENT_DOMAIN = DOMAIN_DEVICE_TRACKER


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up EdgeOS based off an entry."""
    await _async_setup_entry(hass, entry, async_add_entities, CURRENT_DOMAIN, EdgeOSScanner)


async def async_unload_entry(hass, config_entry):
    _LOGGER.info(f"async_unload_entry {CURRENT_DOMAIN}: {config_entry}")

    return True


class EdgeOSScanner(EdgeOSEntity, ScannerEntity):
    """Represent a tracked device."""

    def __init__(self, hass, ha, entity):
        """Initialize the EdgeOS Device Tracker."""
        super().__init__(hass, ha, entity, CURRENT_DOMAIN)

    @property
    def is_connected(self):
        """Return true if the device is connected to the network."""
        return self._entity.get(ENTITY_STATE, False)

    @property
    def source_type(self):
        """Return the source type, eg gps or router, of the device."""
        return self._entity.get(ATTR_SOURCE_TYPE, SOURCE_TYPE_ROUTER)
