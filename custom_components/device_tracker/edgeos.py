"""
Support for Ubiquiti EdgeOS routers.
HEAVILY based on the AsusWRT component
For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/device_tracker.edgeos/
"""
import logging
import sys

from datetime import timedelta
import voluptuous as vol
import homeassistant.helpers.config_validation as cv
from homeassistant.components.device_tracker import (PLATFORM_SCHEMA, SOURCE_TYPE_ROUTER, ATTR_SOURCE_TYPE)
from homeassistant.const import (CONF_HOSTS, CONF_HOST)
from homeassistant.helpers.event import track_time_interval
from homeassistant.util import slugify
from homeassistant.helpers.typing import ConfigType

from custom_components.edgeos import (DATA_EDGEOS, MAC)

_LOGGER = logging.getLogger(__name__)

MIN_TIME_BETWEEN_SCANS = timedelta(seconds=30)

CONF_SUPPORTED_DEVICES = 'supported_devices'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_HOSTS): vol.All(cv.ensure_list, [cv.string])
})


def setup_scanner(hass, config: ConfigType, see, discovery_info=None):
    """Set up the Host objects and return the update function."""
    try:
        _LOGGER.info('Initializing EdgeOS Scanner')

        edgeos = hass.data[DATA_EDGEOS]
        scanner = EdgeOSScanner(hass, edgeos, config, see)

        return scanner.is_initialized

    except Exception as ex:
        exc_type, exc_obj, tb = sys.exc_info()
        line_number = tb.tb_lineno

        _LOGGER.error('Failed to initialize EdgeOS Scanner, Error: {}, Line: {}'.format(str(ex), line_number))

        return False


class EdgeOSScanner:
    """Provide device_tracker support from Unifi WAP client data."""

    def __init__(self, hass, edgeos, config: ConfigType, see) -> None:
        """Initialize the scanner."""

        try:
            self._hosts = config.get(CONF_HOSTS)
            self._edgeos = edgeos
            self._devices = edgeos.get_devices()
            self._attached_devices = []
            self._see = see
            self.is_initialized = False

            _LOGGER.info('Looking for: {}'.format(str(self._hosts)))

            self._update_info()

            track_time_interval(hass, self._update_info, MIN_TIME_BETWEEN_SCANS)

            self.is_initialized = True
        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(
                'Failed to initialize EdgeOS Scanner, Error: {}, Line: {}'.format(str(ex), line_number))

    def _update_info(self, now=None):
        for hostname in self._hosts:
            if self._edgeos.is_device_online(hostname):
                device_name = self._edgeos.get_device_name(hostname)
                mac = self._edgeos.get_device_mac(hostname)

                dev_id = slugify(device_name)

                attributes = {
                    MAC: mac,
                    ATTR_SOURCE_TYPE: SOURCE_TYPE_ROUTER,
                    CONF_HOST: hostname
                }

                self._see(
                    dev_id=dev_id,
                    mac=mac,
                    host_name=hostname,
                    source_type=SOURCE_TYPE_ROUTER,
                    attributes=attributes
                )

    @property
    def is_initialized(self):
        return self._is_initialized

    @is_initialized.setter
    def is_initialized(self, value):
        self._is_initialized = value
