"""
This component provides support for Home Automation Manager (HAM).
For more details about this component, please refer to the documentation at
https://home-assistant.io/components/edgeos/
"""
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import VERSION
from .const import *
from .home_assistant import EdgeOSHomeAssistant

REQUIREMENTS = ['aiohttp']

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass, config):
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a EdgeOS component."""
    _LOGGER.debug(f"Loading EdgeOS domain")

    entry.add_update_listener(async_options_updated)

    entry_data = entry.data
    name = entry_data.get(CONF_NAME)

    if DATA_EDGEOS not in hass.data:
        hass.data[DATA_EDGEOS] = {}

    if name in hass.data[DATA_EDGEOS]:
        _LOGGER.info(f"EdgeOS {name} already defined")
        return False

    ha = EdgeOSHomeAssistant(hass, entry)
    await ha.initialize()

    hass.data[DATA_EDGEOS][name] = ha

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    data = hass.data[DATA_EDGEOS]
    name = entry.data.get(CONF_NAME)

    if name in data:
        edgeos: EdgeOSHomeAssistant = data[name]
        await edgeos.async_remove()

        del hass.data[DATA_EDGEOS][name]

        return True

    return False


async def async_options_updated(hass: HomeAssistant, entry: ConfigEntry):
    """Triggered by config entry options updates."""
    data = hass.data[DATA_EDGEOS]
    name = entry.data.get(CONF_NAME)

    _LOGGER.info(f"async_options_updated {name}, Entry: {entry.as_dict()} ")

    if name in data:
        edgeos: EdgeOSHomeAssistant = data[name]

        await edgeos.async_update_entry(entry, True)
