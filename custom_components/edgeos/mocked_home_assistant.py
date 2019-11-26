"""
This component provides support for Home Automation Manager (HAM).
For more details about this component, please refer to the documentation at
https://home-assistant.io/components/edgeos/
"""
import sys
import logging
import asyncio

from .const import *

_LOGGER = logging.getLogger(__name__)


class EdgeOSMockedHomeAssistant:
    def __init__(self, hass, monitored_interfaces, monitored_devices, unit, scan_interval):
        self._scan_interval = scan_interval
        self._hass = hass
        self._monitored_interfaces = monitored_interfaces
        self._monitored_devices = monitored_devices
        self._unit = unit
        self._unit_size = ALLOWED_UNITS.get(self._unit, BYTE)
        self._loop = asyncio.get_event_loop()

    def initialize(self, edgeos_start, edgeos_stop, edgeos_refresh, edgeos_save_debug_data, edgeos_log_events):
        _LOGGER.info("Starting")
        self._loop.run_until_complete(edgeos_start())
        _LOGGER.info("Stopping")
        self._loop.run_until_complete(edgeos_stop())

        self._loop.close()

    def notify_error(self, ex, line_number):
        _LOGGER.error(f'Error while initializing EdgeOS, exception: {ex}, Line: {line_number}')

    def update(self, interfaces, devices, unknown_devices, system_state, api_last_update, web_socket_last_update):
        _LOGGER.info(f"Interfaces: {interfaces}")
        _LOGGER.info(f"Devices: {devices}")
        _LOGGER.info(f"Unknown devices: {unknown_devices}")
        _LOGGER.info(f"System state: {system_state}")
        _LOGGER.info(f"API Last update: {api_last_update}")
        _LOGGER.info(f"WS last update: {web_socket_last_update}")

    @staticmethod
    def get_device_attributes(key):
        result = DEVICE_SERVICES_STATS_MAP.get(key, {})

        return result

    @staticmethod
    def get_interface_attributes(key):
        all_attributes = {**INTERFACES_MAIN_MAP, **INTERFACES_STATS_MAP}

        result = all_attributes.get(key, {})

        return result

    @staticmethod
    def log_exception(ex, message):
        exc_type, exc_obj, tb = sys.exc_info()
        line_number = tb.tb_lineno

        _LOGGER.error(f'{message}, Error: {ex}, Line: {line_number}')

    def store_data(self, edgeos_data):
        try:
            with open(EDGEOS_DATA_LOG, 'w+') as out:
                out.write(str(edgeos_data))

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(f'Failed to log EdgeOS data, Error: {ex}, Line: {line_number}')
