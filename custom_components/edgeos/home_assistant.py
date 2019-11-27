"""
This component provides support for Home Automation Manager (HAM).
For more details about this component, please refer to the documentation at
https://home-assistant.io/components/edgeos/
"""
import sys
import logging
import voluptuous as vol

from homeassistant.helpers import config_validation as cv
from homeassistant.const import (STATE_OFF, STATE_ON, ATTR_FRIENDLY_NAME)

from homeassistant.const import (EVENT_HOMEASSISTANT_START, EVENT_HOMEASSISTANT_STOP)
from homeassistant.helpers.event import track_time_interval
from homeassistant.util import slugify
from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN

from .const import *

_LOGGER = logging.getLogger(__name__)

SERVICE_LOG_EVENTS_SCHEMA = vol.Schema({
    vol.Required(ATTR_ENABLED): cv.boolean,
})


class EdgeOSHomeAssistant:
    def __init__(self, hass, monitored_interfaces, monitored_devices, unit, scan_interval):
        self._scan_interval = scan_interval
        self._hass = hass
        self._monitored_interfaces = monitored_interfaces
        self._monitored_devices = monitored_devices
        self._unit = unit
        self._unit_size = ALLOWED_UNITS.get(self._unit, BYTE)

    def initialize(self, on_start, on_stop, on_refresh, on_save_debug_data, on_log_events):
        self._hass.services.register(DOMAIN, 'stop', on_stop)
        self._hass.services.register(DOMAIN, 'restart', on_start)
        self._hass.services.register(DOMAIN, 'save_debug_data', on_save_debug_data)
        self._hass.services.register(DOMAIN, 'log_events', on_log_events, schema=SERVICE_LOG_EVENTS_SCHEMA)

        track_time_interval(self._hass, on_refresh, self._scan_interval)

        self._hass.bus.listen_once(EVENT_HOMEASSISTANT_START, on_start)
        self._hass.bus.listen_once(EVENT_HOMEASSISTANT_STOP, on_stop)

    def notify_error(self, ex, line_number):
        _LOGGER.error(f'Error while initializing EdgeOS, exception: {ex}, Line: {line_number}')

        self._hass.components.persistent_notification.create(
            f'Error: {ex}<br /> You will need to restart HA after fixing.',
            title=NOTIFICATION_TITLE,
            notification_id=NOTIFICATION_ID)

    def update(self, interfaces, devices, unknown_devices, system_state, api_last_update, web_socket_last_update):
        self.create_interface_binary_sensors(interfaces)
        self.create_device_binary_sensors(devices)
        self.create_unknown_devices_sensor(unknown_devices)
        self.create_uptime_sensor(system_state, api_last_update, web_socket_last_update)
        self.create_system_status_binary_sensor(system_state, api_last_update, web_socket_last_update)

    def create_device_binary_sensors(self, devices):
        try:
            for hostname in devices:
                host_data = devices.get(hostname, {})

                self.create_device_binary_sensor(hostname, host_data)

        except Exception as ex:
            self.log_exception(ex, 'Failed to updated devices')

    def create_interface_binary_sensors(self, interfaces):
        try:
            for interface in interfaces:
                interface_data = interfaces.get(interface)

                self.create_interface_binary_sensor(interface, interface_data)

        except Exception as ex:
            self.log_exception(ex, f'Failed to update {INTERFACES_KEY}')

    def create_interface_binary_sensor(self, key, data):
        self.create_binary_sensor(key, data, self._monitored_interfaces, SENSOR_TYPE_INTERFACE,
                                  LINK_UP, self.get_interface_attributes)

    def create_device_binary_sensor(self, key, data):
        self.create_binary_sensor(key, data, self._monitored_devices, SENSOR_TYPE_DEVICE,
                                  CONNECTED, self.get_device_attributes)

    def create_binary_sensor(self, key, data, allowed_items, sensor_type, main_attribute, get_attributes):
        try:
            if key in allowed_items:
                entity_name = f'{DEFAULT_NAME} {sensor_type} {key}'
                entity_id = f"{BINARY_SENSOR_DOMAIN}.{slugify(entity_name)}"

                main_entity_details = data.get(main_attribute, FALSE_STR)

                attributes = {
                    ATTR_DEVICE_CLASS: DEVICE_CLASS_CONNECTIVITY,
                    ATTR_FRIENDLY_NAME: entity_name
                }

                for data_item_key in data:
                    if data_item_key != main_attribute:
                        value = data.get(data_item_key)
                        attr = get_attributes(data_item_key)

                        name = attr.get(ATTR_NAME, data_item_key)
                        unit_of_measurement = attr.get(ATTR_UNIT_OF_MEASUREMENT)

                        if unit_of_measurement is None:
                            attributes[name] = value
                        else:
                            name = name.format(self._unit)

                            attributes[name] = (int(value) * BITS_IN_BYTE) / self._unit_size

                if str(main_entity_details).lower() == TRUE_STR:
                    state = STATE_ON
                else:
                    state = STATE_OFF

                current_entity = self._hass.states.get(entity_id)

                attributes[ATTR_LAST_CHANGED] = datetime.now().strftime(DEFAULT_DATE_FORMAT)

                if current_entity is not None and current_entity.state == state:
                    entity_attributes = current_entity.attributes
                    attributes[ATTR_LAST_CHANGED] = entity_attributes.get(ATTR_LAST_CHANGED)

                _LOGGER.debug(f"Creating {entity_name}[{entity_id}] with state {state}, attributes: {attributes}")

                self._hass.states.async_set(entity_id, state, attributes)

        except Exception as ex:
            self.log_exception(ex, f'Failed to create {key} sensor {sensor_type} with the following data: {data}')

    def create_unknown_devices_sensor(self, unknown_devices):
        try:
            entity_name = f"{DEFAULT_NAME} Unknown Devices"
            entity_id = f'{SENSOR_DOMAIN}.{slugify(entity_name)}'

            state = len(unknown_devices)
            if state < 1:
                unknown_devices = None

            attributes = {
                ATTR_FRIENDLY_NAME: entity_name,
                ATTR_UNKNOWN_DEVICES:  unknown_devices
            }

            _LOGGER.debug(f"Creating {entity_name}[{entity_id}] with state {state}, attributes: {attributes}")

            self._hass.states.async_set(entity_id, state, attributes)
        except Exception as ex:
            self.log_exception(ex, f'Failed to create unknown device sensor, Data: {unknown_devices}')

    def create_uptime_sensor(self, system_state, api_last_update, web_socket_last_update):
        try:
            entity_name = f'{DEFAULT_NAME} {ATTR_SYSTEM_UPTIME}'
            entity_id = f'{SENSOR_DOMAIN}.{slugify(entity_name)}'

            state = system_state.get(UPTIME, 0)
            attributes = {}

            if system_state is not None:
                attributes = {
                    ATTR_UNIT_OF_MEASUREMENT: ATTR_SECONDS,
                    ATTR_FRIENDLY_NAME: entity_name,
                    ATTR_API_LAST_UPDATE: api_last_update.strftime(DEFAULT_DATE_FORMAT),
                    ATTR_WEB_SOCKET_LAST_UPDATE: web_socket_last_update.strftime(DEFAULT_DATE_FORMAT)
                }

                for key in system_state:
                    if key != UPTIME:
                        attributes[key] = system_state[key]

            _LOGGER.debug(f"Creating {entity_name}[{entity_id}] with state {state}, attributes: {attributes}")

            self._hass.states.async_set(entity_id, state, attributes)
        except Exception as ex:
            self.log_exception(ex, 'Failed to create system sensor')

    def create_system_status_binary_sensor(self, system_state, api_last_update, web_socket_last_update):
        try:
            entity_name = f'{DEFAULT_NAME} {ATTR_SYSTEM_STATUS}'
            entity_id = f'{BINARY_SENSOR_DOMAIN}.{slugify(entity_name)}'

            state = STATE_OFF
            attributes = {}

            if system_state is not None:
                attributes = {
                    ATTR_DEVICE_CLASS: DEVICE_CLASS_CONNECTIVITY,
                    ATTR_FRIENDLY_NAME: entity_name,
                    ATTR_API_LAST_UPDATE: api_last_update.strftime(DEFAULT_DATE_FORMAT),
                    ATTR_WEB_SOCKET_LAST_UPDATE: web_socket_last_update.strftime(DEFAULT_DATE_FORMAT)
                }

                for key in system_state:
                    if key != IS_ALIVE:
                        attributes[key] = system_state[key]

                is_alive = system_state.get(IS_ALIVE, False)

                if is_alive:
                    state = STATE_ON

            _LOGGER.debug(f"Creating {entity_name}[{entity_id}] with state {state}, attributes: {attributes}")

            self._hass.states.async_set(entity_id, state, attributes)
        except Exception as ex:
            self.log_exception(ex, 'Failed to create system status binary sensor')

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
            path = self._hass.config.path(EDGEOS_DATA_LOG)

            with open(path, 'w+') as out:
                out.write(str(edgeos_data))

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(f'Failed to log EdgeOS data, Error: {ex}, Line: {line_number}')
