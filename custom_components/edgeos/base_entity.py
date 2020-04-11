import logging

from typing import Optional

from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.entity_registry import async_get_registry, EntityRegistry

from .const import *

_LOGGER = logging.getLogger(__name__)


class EdgeOSEntity(RestoreEntity):
    """Representation a binary sensor that is updated by EdgeOS."""

    def __init__(self, hass, ha, entity, current_domain):
        """Initialize the EdgeOS Binary Sensor."""
        self._hass = hass
        self._entity = entity
        self._remove_dispatcher = None
        self._ha = ha
        self._entity_manager = ha.entity_manager
        self._device_manager = ha.device_manager
        self._current_domain = current_domain

    @property
    def unique_id(self) -> Optional[str]:
        """Return the name of the node."""
        return f"{DEFAULT_NAME}-{self._current_domain}-{self.name}"

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
        """Return the name of the binary sensor."""
        return self._entity.get(ENTITY_NAME)

    @property
    def icon(self) -> Optional[str]:
        """Return the icon of the sensor."""
        return self._entity.get(ENTITY_ICON)

    @property
    def device_state_attributes(self):
        """Return true if the binary sensor is on."""
        return self._entity.get(ENTITY_ATTRIBUTES, {})

    async def async_added_to_hass(self):
        """Register callbacks."""
        await super().async_added_to_hass()
        state = await self.async_get_last_state()

        if not state:
            return

        self._current_domain = state.domain

        entity_registry = await async_get_registry(self._hass)

        entity_from_reg = entity_registry.async_get(state.entity_id)

        self._entity = {
            ENTITY_ICON: entity_from_reg.original_icon,
            ENTITY_NAME: entity_from_reg.original_name,
            ENTITY_ATTRIBUTES: state.attributes,
            ENTITY_STATE: state.state
        }

        config_entry_id = entity_from_reg.config_entry_id

        entry = self._hass.config_entries.async_get_entry(config_entry_id)
        name = entry.data.get(CONF_NAME)

        ha = _get_ha(self._hass, name)

        self._ha = ha
        self._entity_manager = ha.entity_manager
        self._device_manager = ha.device_manager

        _LOGGER.info(f"async_added_to_hass: {self.unique_id}")

        self._remove_dispatcher = async_dispatcher_connect(self._hass,
                                                           SIGNALS[self._current_domain],
                                                           self._schedule_immediate_update)

        self._entity_manager.set_entity_status(self._current_domain, self.name, ENTITY_STATUS_READY)

    async def async_will_remove_from_hass(self) -> None:
        if self._remove_dispatcher is not None:
            self._remove_dispatcher()

    async def async_update_data(self):
        if self._entity_manager is None:
            _LOGGER.debug(f"Cannot update {self._current_domain} - Entity Manager is None | {self.name}")
        else:
            self._entity = self._entity_manager.get_entity(self._current_domain, self.name)

            if self._entity is None:
                _LOGGER.debug(f"Cannot update {self._current_domain} - Entity was not found | {self.name}")

                self._entity = {}
                await self.async_remove()
            elif self._entity[ENTITY_STATUS] == ENTITY_STATUS_CANCELLED:
                _LOGGER.debug(f"Update {self._current_domain} - Entity was removed | {self.name}")

                self._entity_manager.delete_entity(self._current_domain, self.name)

                self._entity = {}
                await self.async_remove()
            else:
                _LOGGER.debug(f"Update {self._current_domain} -> {self.name}")

                self._entity_manager.set_entity_status(self._current_domain, self.name, ENTITY_STATUS_READY)

    @callback
    def _schedule_immediate_update(self):
        self.hass.async_add_job(self.async_update_data)

        self.async_schedule_update_ha_state(True)


def _get_ha(hass, name):
    ha_data = hass.data.get(DATA_EDGEOS, {})
    ha = ha_data.get(name)

    return ha