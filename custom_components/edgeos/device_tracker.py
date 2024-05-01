"""
Support for Ubiquiti EdgeOS routers.
HEAVILY based on the AsusWRT component
For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/device_tracker.edgeos/
"""
import logging

from homeassistant.components.device_tracker import (
    ATTR_IP,
    ATTR_MAC,
    ScannerEntity,
    SourceType,
)
from homeassistant.const import ATTR_ICON, Platform
from homeassistant.core import HomeAssistant

from .common.base_entity import IntegrationBaseEntity, async_setup_base_entry
from .common.consts import ATTR_ATTRIBUTES, ATTR_IS_ON
from .common.entity_descriptions import IntegrationDeviceTrackerEntityDescription
from .managers.coordinator import Coordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the entity."""
    await async_setup_base_entry(
        hass,
        entry,
        Platform.DEVICE_TRACKER,
        IntegrationCoreScannerEntity,
        async_add_entities,
    )


class IntegrationCoreScannerEntity(IntegrationBaseEntity, ScannerEntity):
    """Represent a tracked device."""

    def __init__(
        self,
        hass: HomeAssistant,
        entity_description: IntegrationDeviceTrackerEntityDescription,
        coordinator: Coordinator,
        item_id: str | None,
    ):
        super().__init__(hass, entity_description, coordinator, item_id)

        self._attr_ip_address: str | None = None
        self._attr_mac_address: str | None = None
        self._attr_source_type: SourceType | str | None = SourceType.ROUTER
        self._attr_is_connected: bool = False

    @property
    def ip_address(self) -> str | None:
        """Return the primary ip address of the device."""
        return self._attr_ip_address

    @property
    def mac_address(self) -> str | None:
        """Return the mac address of the device."""
        return self._attr_mac_address

    @property
    def is_connected(self) -> bool:
        """Return true if the device is connected to the network."""
        return self._attr_is_connected

    @property
    def source_type(self) -> SourceType | str:
        """Return the source type."""
        return self._attr_source_type

    def update_component(self, data):
        """Fetch new state parameters for the sensor."""
        if data is not None:
            is_connected = data.get(ATTR_IS_ON)
            attributes = data.get(ATTR_ATTRIBUTES)
            icon = data.get(ATTR_ICON)

            self._attr_is_connected = is_connected
            self._attr_ip_address = attributes.get(ATTR_IP)
            self._attr_mac_address = attributes.get(ATTR_MAC)

            self._attr_extra_state_attributes = {
                attribute: attributes[attribute]
                for attribute in attributes
                if attribute not in [ATTR_IP, ATTR_MAC]
            }

            if icon is not None:
                self._attr_icon = icon

        else:
            self._attr_is_connected = False
