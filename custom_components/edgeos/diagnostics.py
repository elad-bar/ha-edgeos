"""Diagnostics support for Tuya."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.device_registry import DeviceEntry

from .common.consts import DEVICE_DATA_MAC, DOMAIN, INTERFACE_DATA_NAME
from .common.enums import DeviceTypes
from .managers.coordinator import Coordinator

_LOGGER = logging.getLogger(__name__)


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    _LOGGER.debug("Starting diagnostic tool")

    coordinator = hass.data[DOMAIN][entry.entry_id]

    return _async_get_diagnostics(hass, coordinator, entry)


async def async_get_device_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry, device: DeviceEntry
) -> dict[str, Any]:
    """Return diagnostics for a device entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    return _async_get_diagnostics(hass, coordinator, entry, device)


@callback
def _async_get_diagnostics(
    hass: HomeAssistant,
    coordinator: Coordinator,
    entry: ConfigEntry,
    device: DeviceEntry | None = None,
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    _LOGGER.debug("Getting diagnostic information")

    debug_data = coordinator.get_debug_data()

    data = {
        "disabled_by": entry.disabled_by,
        "disabled_polling": entry.pref_disable_polling,
    }

    if device:
        data["config"] = debug_data["config"]
        data["data"] = debug_data["data"]
        data["processors"] = debug_data["processors"]

        device_data = coordinator.get_device_data(device.model, device.identifiers)

        data |= _async_device_as_dict(
            hass,
            device.identifiers,
            device_data,
        )

    else:
        _LOGGER.debug("Getting diagnostic information for all devices")

        data = {
            "config": debug_data["config"],
            "data": debug_data["data"],
            "processors": debug_data["processors"],
        }

        processor_data = debug_data["processors"]
        system_data = processor_data[DeviceTypes.SYSTEM]
        device_data = processor_data[DeviceTypes.DEVICE]
        interface_data = processor_data[DeviceTypes.INTERFACE]

        data.update(
            devices=[
                _async_device_as_dict(
                    hass,
                    coordinator.get_device_identifiers(
                        DeviceTypes.DEVICE, item.get(DEVICE_DATA_MAC)
                    ),
                    item,
                )
                for item in device_data
            ],
            interfaces=[
                _async_device_as_dict(
                    hass,
                    coordinator.get_device_identifiers(
                        DeviceTypes.INTERFACE, item.get(INTERFACE_DATA_NAME)
                    ),
                    item,
                )
                for item in interface_data
            ],
            system=_async_device_as_dict(
                hass,
                coordinator.get_device_identifiers(DeviceTypes.SYSTEM),
                system_data,
            ),
        )

    return data


@callback
def _async_device_as_dict(
    hass: HomeAssistant, identifiers, additional_data: dict
) -> dict[str, Any]:
    """Represent an EdgeOS based device as a dictionary."""
    device_registry = dr.async_get(hass)
    entity_registry = er.async_get(hass)

    ha_device = device_registry.async_get_device(identifiers=identifiers)
    data = {}

    if ha_device:
        data["device"] = {
            "name": ha_device.name,
            "name_by_user": ha_device.name_by_user,
            "disabled": ha_device.disabled,
            "disabled_by": ha_device.disabled_by,
            "data": additional_data,
            "entities": [],
        }

        ha_entities = er.async_entries_for_device(
            entity_registry,
            device_id=ha_device.id,
            include_disabled_entities=True,
        )

        for entity_entry in ha_entities:
            state = hass.states.get(entity_entry.entity_id)
            state_dict = None
            if state:
                state_dict = dict(state.as_dict())

                # The context doesn't provide useful information in this case.
                state_dict.pop("context", None)

            data["device"]["entities"].append(
                {
                    "disabled": entity_entry.disabled,
                    "disabled_by": entity_entry.disabled_by,
                    "entity_category": entity_entry.entity_category,
                    "device_class": entity_entry.device_class,
                    "original_device_class": entity_entry.original_device_class,
                    "icon": entity_entry.icon,
                    "original_icon": entity_entry.original_icon,
                    "unit_of_measurement": entity_entry.unit_of_measurement,
                    "state": state_dict,
                }
            )

    return data
