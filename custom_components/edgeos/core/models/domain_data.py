from __future__ import annotations

from collections.abc import Callable
import logging
from typing import Any

from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from ..models.entity_data import EntityData

_LOGGER = logging.getLogger(__name__)


class DomainData:
    name: str
    async_add_devices: AddEntitiesCallback
    initializer: Callable[[HomeAssistant, EntityData], Any]

    def __init__(
        self,
        name,
        async_add_devices: AddEntitiesCallback,
        initializer: Callable[[HomeAssistant, EntityData], Any],
    ):
        self.name = name
        self.async_add_devices = async_add_devices
        self.initializer = initializer

        _LOGGER.info(f"Creating domain data for {name}")

    def __repr__(self):
        obj = {CONF_NAME: self.name}

        to_string = f"{obj}"

        return to_string
