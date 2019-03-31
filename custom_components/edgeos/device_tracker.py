"""
Support for Ubiquiti EdgeOS routers.
HEAVILY based on the AsusWRT component
For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/device_tracker.edgeos/
"""
import logging
import sys

import voluptuous as vol
import homeassistant.helpers.config_validation as cv
from homeassistant.components.device_tracker import (PLATFORM_SCHEMA, SOURCE_TYPE_ROUTER, ATTR_SOURCE_TYPE)
from homeassistant.components.device_tracker import DeviceScanner
from homeassistant.const import (CONF_HOSTS, CONF_HOST)
from homeassistant.helpers.typing import ConfigType

from homeassistant.components.device_tracker import DOMAIN as DEVICE_TRACKER_DOMAIN
from .const import *

_LOGGER = logging.getLogger(__name__)
DEPENDENCIES = [DOMAIN]

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_HOSTS): vol.All(cv.ensure_list, [cv.string])
})


def get_scanner(hass, config: ConfigType):
    """Set up the Host objects and return the update function."""
    try:
        conf = config[DEVICE_TRACKER_DOMAIN]

        _LOGGER.info(f'Getting EdgeOS Scanner, Configuration: {conf}')

        edgeos_data = hass.data[DATA_EDGEOS]
        hosts = conf.get(CONF_HOSTS, [])

        scanner = EdgeOSScanner(edgeos_data, hosts)

        return scanner if scanner.is_initialized() else None

    except Exception as ex:
        exc_type, exc_obj, tb = sys.exc_info()
        line_number = tb.tb_lineno

        _LOGGER.error(f'Failed to initialize EdgeOS Scanner, Error: {str(ex)}, Line: {line_number}')

        return None


class EdgeOSScanner(DeviceScanner):
    """Provide device_tracker support from Unifi WAP client data."""

    def __init__(self, edgeos, hosts):
        """Initialize the scanner."""

        try:
            self._hosts = hosts
            self._edgeos = edgeos
            self._attached_devices = {}
            self._is_initialized = False

            _LOGGER.info(f'Initializing EdgeOS Scanner, Looking for: {str(self._hosts)}')

            self._is_initialized = True
        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(f'Failed to initialize EdgeOS Scanner, Error: {str(ex)}, Line: {line_number}')

    def scan_devices(self):
        """Scan for new devices and return a list with found device IDs."""
        try:
            _LOGGER.debug('Start scanning for new devices')

            online_devices = []

            for hostname in self._hosts:
                is_online = self._edgeos.is_device_online(hostname)

                if is_online:
                    online_devices.append(hostname)

            _LOGGER.debug('Following online devices found: {}'.format(online_devices))

            return online_devices

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(f'Failed to scan_devices, Error: {str(ex)}, Line: {line_number}')

            return None

    def get_device_name(self, device):
        try:
            """Return the name of the given device or None if we don't know."""
            device_name = self._edgeos.get_device_name(device)

            return device_name

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(f'Failed to get_device_name, Device: {device}, Error: {str(ex)}, Line: {line_number}')

            return None

    def get_extra_attributes(self, device):
        """Return the IP of the given device."""
        device_data = self._edgeos.get_device(device)

        additional_data = {
            ATTR_SOURCE_TYPE: SOURCE_TYPE_ROUTER,
            CONF_HOST: device
        }

        attributes = {**device_data, **additional_data}

        return attributes

    def is_initialized(self):
        return self._is_initialized
