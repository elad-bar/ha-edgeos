from homeassistant.core import HomeAssistant

from ...core.helpers.const import DATA


def get_ha(hass: HomeAssistant, entry_id):
    ha_data = hass.data.get(DATA, {})
    ha = ha_data.get(entry_id)

    return ha
