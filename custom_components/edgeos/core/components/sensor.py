from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant

from ..helpers.const import *
from ..models.base_entity import BaseEntity
from ..models.entity_data import EntityData


class CoreSensor(SensorEntity, BaseEntity):
    """Representation a binary sensor that is updated by EdgeOS."""

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self.entity.state

    @staticmethod
    def get_component(hass: HomeAssistant, entity: EntityData):
        sensor = CoreSensor()
        sensor.initialize(hass, entity, DOMAIN_SENSOR)

        return sensor

    @staticmethod
    def get_domain():
        return DOMAIN_SENSOR
