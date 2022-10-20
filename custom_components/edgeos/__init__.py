"""
Init.
"""
import logging
import sys

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .component.helpers import async_set_ha, clear_ha, get_ha
from .component.helpers.const import *

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass, config):
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a component."""
    initialized = False

    try:
        _LOGGER.debug(f"Starting async_setup_entry of {DOMAIN}")
        entry.add_update_listener(async_options_updated)

        await async_set_ha(hass, entry)

        initialized = True

    except Exception as ex:
        exc_type, exc_obj, tb = sys.exc_info()
        line_number = tb.tb_lineno

        _LOGGER.error(f"Failed to load integration, error: {ex}, line: {line_number}")

    return initialized


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    ha = get_ha(hass, entry.entry_id)

    if ha is not None:
        await ha.async_remove(entry)

    clear_ha(hass, entry.entry_id)

    return True


async def async_options_updated(hass: HomeAssistant, entry: ConfigEntry):
    """Triggered by config entry options updates."""
    _LOGGER.info(f"async_options_updated, Entry: {entry.as_dict()} ")

    ha = get_ha(hass, entry.entry_id)

    if ha is not None:
        await ha.async_update_entry(entry)
