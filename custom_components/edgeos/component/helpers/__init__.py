import logging
import sys

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.core import Event, HomeAssistant

from ...component.managers.home_assistant import EdgeOSHomeAssistantManager
from ...core.helpers.const import DATA

_LOGGER = logging.getLogger(__name__)


async def async_set_ha(hass: HomeAssistant, entry: ConfigEntry):
    try:
        if DATA not in hass.data:
            hass.data[DATA] = {}

        instance = EdgeOSHomeAssistantManager(hass)

        await instance.async_init(entry)

        hass.data[DATA][entry.entry_id] = instance

        async def _async_unload(_: Event) -> None:
            await instance.async_unload()

        entry.async_on_unload(
            hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, _async_unload)
        )
    except Exception as ex:
        exc_type, exc_obj, tb = sys.exc_info()
        line_number = tb.tb_lineno

        _LOGGER.error(f"Failed to async_set_ha, error: {ex}, line: {line_number}")


def get_ha(hass: HomeAssistant, entry_id) -> EdgeOSHomeAssistantManager:
    ha_data = hass.data.get(DATA, {})
    ha = ha_data.get(entry_id)

    return ha


def clear_ha(hass: HomeAssistant, entry_id):
    if DATA not in hass.data:
        hass.data[DATA] = {}

    del hass.data[DATA][entry_id]
