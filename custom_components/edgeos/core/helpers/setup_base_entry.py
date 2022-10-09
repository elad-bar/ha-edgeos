import logging
import sys
from typing import Any, Callable

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from ..helpers.const import *
from ..models.domain_data import DomainData
from ..models.entity_data import EntityData

_LOGGER = logging.getLogger(__name__)


async def async_setup_base_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_devices: AddEntitiesCallback,
    domain: str,
    initializer: Callable[[HomeAssistant, EntityData], Any],
):
    """Set up base entity an entry."""
    _LOGGER.debug(f"Starting async_setup_entry {domain}")

    try:
        ha_data = hass.data.get(DATA, dict())

        ha = ha_data.get(entry.entry_id)

        entity_manager = ha.entity_manager

        domain_data = DomainData(domain, async_add_devices, initializer)

        _LOGGER.debug(f"{domain} domain data: {domain_data}")

        entity_manager.set_domain_data(domain_data)
    except Exception as ex:
        exc_type, exc_obj, tb = sys.exc_info()
        line_number = tb.tb_lineno

        _LOGGER.error(f"Failed to load {domain}, error: {ex}, line: {line_number}")
