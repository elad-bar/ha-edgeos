"""
Support for device tracker.
"""
from __future__ import annotations

import logging

from homeassistant.components.device_tracker import ATTR_SOURCE_TYPE, SOURCE_TYPE_ROUTER
from homeassistant.components.device_tracker.config_entry import ScannerEntity
from homeassistant.components.device_tracker.const import ATTR_IP, ATTR_MAC
from homeassistant.core import HomeAssistant

from ..helpers.const import *
from ..models.base_entity import BaseEntity
from ..models.entity_data import EntityData

_LOGGER = logging.getLogger(__name__)


class CoreScanner(BaseEntity, ScannerEntity):
    """Represent a tracked device."""

    @property
    def ip_address(self) -> str | None:
        """Return the primary ip address of the device."""
        return self.entity.details.get(ATTR_IP)

    @property
    def mac_address(self) -> str | None:
        """Return the mac address of the device."""
        return self.entity.details.get(ATTR_MAC)

    @property
    def is_connected(self):
        """Return true if the device is connected to the network."""
        return self.entity.state

    @property
    def source_type(self):
        """Return the source type."""
        return self.entity.attributes.get(ATTR_SOURCE_TYPE, SOURCE_TYPE_ROUTER)

    @staticmethod
    def get_component(hass: HomeAssistant, entity: EntityData):
        device_tracker = CoreScanner()
        device_tracker.initialize(hass, entity, DOMAIN_DEVICE_TRACKER)

        return device_tracker

    @staticmethod
    def get_domain():
        return DOMAIN_DEVICE_TRACKER
