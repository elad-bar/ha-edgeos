"""
Support for Ubiquiti EdgeOS routers.
HEAVILY based on the AsusWRT component
For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/device_tracker.edgeos/
"""
import logging

from .core.components.device_tracker import CoreScanner
from .core.helpers.setup_base_entry import async_setup_base_entry

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_devices):
    """Set up the entity."""
    await async_setup_base_entry(
        hass,
        config_entry,
        async_add_devices,
        CoreScanner.get_domain(),
        CoreScanner.get_component,
    )


async def async_unload_entry(hass, config_entry):
    _LOGGER.info(f"Unload entry for {CoreScanner.get_domain()} domain: {config_entry}")

    return True


async def async_remove_entry(hass, entry) -> None:
    _LOGGER.info(f"Remove entry for {CoreScanner.get_domain()} entry: {entry}")
