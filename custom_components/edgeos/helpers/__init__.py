import sys
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import *
from ..managers.home_assistant import EdgeOSHomeAssistant
from ..managers.password_manager import PasswordManager

_LOGGER = logging.getLogger(__name__)


def clear_ha(hass: HomeAssistant, name):
    if DATA_EDGEOS not in hass.data:
        hass.data[DATA_EDGEOS] = dict()

    del hass.data[DATA_EDGEOS][name]


def get_ha(hass: HomeAssistant, name):
    ha_data = hass.data.get(DATA_EDGEOS, dict())
    ha = ha_data.get(name)

    return ha


async def async_set_ha(hass: HomeAssistant, name, entry: ConfigEntry):
    try:
        if DATA_EDGEOS not in hass.data:
            hass.data[DATA_EDGEOS] = dict()

        if PASSWORD_MANAGER_EDGEOS not in hass.data:
            hass.data[PASSWORD_MANAGER_EDGEOS] = PasswordManager(hass)

        password_manager = hass.data[PASSWORD_MANAGER_EDGEOS]

        if name in hass.data[DATA_EDGEOS]:
            _LOGGER.info(f"EdgeOS {name} already defined")
            return False

        ha = EdgeOSHomeAssistant(hass, entry, password_manager)
        await ha.async_init(entry)
    except Exception as ex:
        exc_type, exc_obj, tb = sys.exc_info()
        line_number = tb.tb_lineno

        _LOGGER.error(f"Failed to async_set_ha, error: {ex}, line: {line_number}")
