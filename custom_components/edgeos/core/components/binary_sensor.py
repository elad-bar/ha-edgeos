"""
Support for binary sensors.
"""
from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant

from ..helpers.const import *
from ..models.base_entity import BaseEntity
from ..models.entity_data import EntityData


class CoreBinarySensor(BinarySensorEntity, BaseEntity):
    """Representation a binary sensor that is updated."""
    @property
    def is_on(self):
        """Return true if the binary sensor is on."""
        return self.entity.state == STATE_ON

    @staticmethod
    def get_component(hass: HomeAssistant, entity: EntityData):
        binary_sensor = CoreBinarySensor()
        binary_sensor.initialize(hass, entity, DOMAIN_BINARY_SENSOR)

        return binary_sensor

    @staticmethod
    def get_domain():
        return DOMAIN_BINARY_SENSOR
