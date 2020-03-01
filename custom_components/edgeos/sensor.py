"""
Support for EdgeOS binary sensors.
For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/binary_sensor.edgeos/
"""
import sys
import logging
from typing import Optional, Union

from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from homeassistant.helpers.entity import Entity

from .const import *

_LOGGER = logging.getLogger(__name__)

CURRENT_DOMAIN = DOMAIN_SENSOR


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up EdgeOS based off an entry."""
    _LOGGER.debug(f"Starting async_setup_entry {CURRENT_DOMAIN}")

    try:
        entry_data = entry.data
        name = entry_data.get(CONF_NAME)
        entities = []

        ha = _get_ha(hass, name)
        entity_manager = ha.entity_manager

        if entity_manager is not None:
            entities_data = entity_manager.get_entities(CURRENT_DOMAIN)
            for entity_name in entities_data:
                entity = entities_data[entity_name]

                entity = EdgeOSSensor(hass, ha, entity)

                _LOGGER.debug(f"Setup {CURRENT_DOMAIN}: {entity.name} | {entity.unique_id}")

                entities.append(entity)

                entity_manager.set_entry_loaded_state(CURRENT_DOMAIN, True)

        async_add_entities(entities, True)
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

class EdgeOSSensor(Entity):
    """Representation a binary sensor that is updated by EdgeOS."""

    def __init__(self, hass, ha, entity):
        """Initialize the EdgeOS Sensor."""
        self._hass = hass
        self._entity = entity
        self._remove_dispatcher = None
        self._ha = ha
        self._entity_manager = ha.entity_manager
        self._device_manager = ha.device_manager

    @property
    def unique_id(self) -> Optional[str]:
        """Return the name of the node."""
        return f"{DEFAULT_NAME}-{CURRENT_DOMAIN}-{self.name}"

    @property
    def device_info(self):
        device_name = self._entity.get(ENTITY_DEVICE_NAME)

        return self._device_manager.get(device_name)

    @property
    def should_poll(self):
        """Return the polling state."""
        return False

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._entity.get(ENTITY_NAME)

    @property
    def icon(self) -> Optional[str]:
        """Return the icon of the sensor."""
        return self._entity.get(ENTITY_ICON)

    @property
    def state(self) -> Union[None, str, int, float]:
        """Return the state of the sensor."""
        return self._entity.get(ENTITY_STATE)

    @property
    def device_state_attributes(self):
        """Return true if the sensor is on."""
        return self._entity.get(ENTITY_ATTRIBUTES, {})

    async def async_added_to_hass(self):
        """Register callbacks."""
        self._remove_dispatcher = async_dispatcher_connect(self._hass, SIGNALS[CURRENT_DOMAIN], self.update_data)

    async def async_will_remove_from_hass(self) -> None:
        if self._remove_dispatcher is not None:
            self._remove_dispatcher()

    @callback
    def update_data(self):
        self.hass.async_add_job(self.async_update_data)

    async def async_update_data(self):
        if self._entity_manager is None:
            _LOGGER.debug(f"Cannot update {CURRENT_DOMAIN} - Entity Manager is None | {self.name}")
        else:
            self._entity = self._entity_manager.get_entity(CURRENT_DOMAIN, self.name)

            if self._entity is None:
                _LOGGER.debug(f"Cannot update {CURRENT_DOMAIN} - Entity was not found | {self.name}")

                self._entity = {}
                await self.async_remove()
            else:
                _LOGGER.debug(f"Update {CURRENT_DOMAIN} -> {self.name}")

                self.async_schedule_update_ha_state(True)


def _get_ha(hass, host):
    ha_data = hass.data.get(DATA_EDGEOS, {})
    ha = ha_data.get(host)

    return ha
