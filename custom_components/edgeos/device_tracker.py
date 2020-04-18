"""
Support for Ubiquiti EdgeOS routers.
HEAVILY based on the AsusWRT component
For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/device_tracker.edgeos/
"""
import logging

from homeassistant.components.device_tracker import ATTR_SOURCE_TYPE, SOURCE_TYPE_ROUTER
from homeassistant.components.device_tracker.config_entry import ScannerEntity
from homeassistant.core import HomeAssistant

from .models.base_entity import EdgeOSEntity, async_setup_base_entry
from .helpers.const import *
from .models.entity_data import EntityData

_LOGGER = logging.getLogger(__name__)
DEPENDENCIES = [DOMAIN]

CURRENT_DOMAIN = DOMAIN_DEVICE_TRACKER


def get_device_tracker(hass: HomeAssistant, host: str, entity: EntityData):
    device_tracker = EdgeOSScanner()
    device_tracker.initialize(hass, host, entity, CURRENT_DOMAIN)

    return device_tracker


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up EdgeOS based off an entry."""
    await async_setup_base_entry(hass, entry, async_add_entities, CURRENT_DOMAIN, get_device_tracker)


async def async_unload_entry(hass, config_entry):
    _LOGGER.info(f"async_unload_entry {CURRENT_DOMAIN}: {config_entry}")

    return True


class EdgeOSScanner(EdgeOSEntity, ScannerEntity):
    """Represent a tracked device."""

    @property
    def is_connected(self):
        """Return true if the device is connected to the network."""
        return self.entity.state

    @property
    def source_type(self):
        """Return the source type, eg gps or router, of the device."""
        return self.entity.attributes.get(ATTR_SOURCE_TYPE, SOURCE_TYPE_ROUTER)

    async def async_added_to_hass_local(self):
        _LOGGER.info(f"Added new {self.name}")

    def _immediate_update(self, previous_state: bool):
        if previous_state != self.entity.state:
            _LOGGER.debug(f"{self.name} updated from {previous_state} to {self.entity.state}")

        super()._immediate_update(previous_state)
