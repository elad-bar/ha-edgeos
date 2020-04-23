import logging
import sys

from homeassistant.helpers.device_registry import async_get_registry

from ..helpers.const import *
from .data_manager import EdgeOSData

_LOGGER = logging.getLogger(__name__)


class DeviceManager:
    def __init__(self, hass, ha):
        self._hass = hass
        self._ha = ha

        self._devices = {}

        self._data_manager = self._ha.data_manager

    @property
    def data_manager(self) -> EdgeOSData:
        return self._data_manager

    async def async_remove_entry(self, entry_id):
        dr = await async_get_registry(self._hass)
        dr.async_clear_config_entry(entry_id)

    async def async_remove(self):
        for device_name in self._devices:
            await self.delete_device(device_name)

    def get(self, name):
        return self._devices.get(name, {})

    def set(self, name, device_info):
        self._devices[name] = device_info

    def update(self):
        self.generate_system_device()

    def generate_system_device(self):
        try:
            hostname = self.data_manager.hostname
            product = self.data_manager.product
            version = self.data_manager.version

            if hostname is None or product is None:
                _LOGGER.info(f"Cannot generate {DEFAULT_NAME} device")

                return

            current_device_info = self.get(DEFAULT_NAME)

            device_name = f"{MANUFACTURER} {product} {hostname}"

            device_info = {
                "identifiers": {(DEFAULT_NAME, device_name)},
                "name": device_name,
                "manufacturer": MANUFACTURER,
                "model": product,
                "sw_version": version,
            }

            if current_device_info.get("name", "") != device_name:
                _LOGGER.info(f"{DEFAULT_NAME} device created: {device_info}")

                self.set(DEFAULT_NAME, device_info)

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(
                f"Failed to generate system device, Error: {ex}, Line: {line_number}"
            )

    async def delete_device(self, name):
        _LOGGER.info(f"Deleting device {name}")

        device = self._devices[name]

        device_identifiers = device.get("identifiers")
        device_connections = device.get("connections", {})

        dr = await async_get_registry(self._hass)

        device = dr.async_get_device(device_identifiers, device_connections)

        if device is not None:
            dr.async_remove_device(device.id)
