"""
This component provides support for Home Automation Manager (HAM).
For more details about this component, please refer to the documentation at
https://home-assistant.io/components/edgeos/
"""
import sys
import logging

from homeassistant.const import (STATE_OFF, STATE_ON, ATTR_FRIENDLY_NAME, STATE_UNKNOWN, EVENT_TIME_CHANGED)

from homeassistant.const import (EVENT_HOMEASSISTANT_START, EVENT_HOMEASSISTANT_STOP)
from homeassistant.helpers.event import track_time_interval
from homeassistant.util import slugify

from .const import *

_LOGGER = logging.getLogger(__name__)


class EdgeOSHomeAssistant:
    def __init__(self, hass, monitored_interfaces, monitored_devices, unit, scan_interval):
        self._scan_interval = scan_interval
        self._hass = hass
        self._monitored_interfaces = monitored_interfaces
        self._monitored_devices = monitored_devices
        self._unit = unit
        self._unit_size = ALLOWED_UNITS.get(self._unit, BYTE)

    def initialize(self, edgeos_initialize, edgeos_stop, edgeos_refresh, edgeos_save_debug_data):
        self._hass.services.register(DOMAIN, 'stop', edgeos_stop)
        self._hass.services.register(DOMAIN, 'restart', edgeos_initialize)
        self._hass.services.register(DOMAIN, 'save_debug_data', edgeos_save_debug_data)

        track_time_interval(self._hass, edgeos_refresh, self._scan_interval)

        self._hass.bus.listen_once(EVENT_HOMEASSISTANT_START, edgeos_initialize)
        self._hass.bus.listen_once(EVENT_HOMEASSISTANT_STOP, edgeos_stop)

    def notify_error(self, ex, line_number):
        _LOGGER.error(f'Error while initializing EdgeOS, exception: {ex}, Line: {line_number}')

        self._hass.components.persistent_notification.create(
            f'Error: {ex}<br /> You will need to restart hass after fixing.',
            title=NOTIFICATION_TITLE,
            notification_id=NOTIFICATION_ID)

    def update(self, interfaces, devices, unknown_devices, system_state, api_last_update, web_socket_last_update):
        self.create_interface_sensors(interfaces)
        self.create_device_sensors(devices)
        self.create_unknown_devices_sensor(unknown_devices)
        self.create_system_sensor(system_state, api_last_update, web_socket_last_update)

    def create_device_sensors(self, devices):
        try:
            for hostname in devices:
                host_data = devices.get(hostname, {})

                self.create_device_sensor(hostname, host_data)

        except Exception as ex:
            self.log_exception(ex, 'Failed to updated devices')

    def create_interface_sensors(self, interfaces):
        try:
            for interface in interfaces:
                interface_data = interfaces.get(interface)

                self.create_interface_sensor(interface, interface_data)

        except Exception as ex:
            error_message = f'Failed to update {INTERFACES_KEY}'

            self.log_exception(ex, error_message)

    def create_interface_sensor(self, key, data):
        self.create_sensor(key, data, self._monitored_interfaces, ENTITY_ID_INTERFACE_BINARY_SENSOR,
                           SENSOR_TYPE_INTERFACE, LINK_UP, self.get_interface_attributes)

    def create_device_sensor(self, key, data):
        self.create_sensor(key, data, self._monitored_devices, ENTITY_ID_DEVICE_BINARY_SENSOR, SENSOR_TYPE_DEVICE,
                           CONNECTED, self.get_device_attributes)

    def create_sensor(self, key, data, allowed_items, entity_id_template, sensor_type, main_attribute, get_attributes):
        try:
            if key in allowed_items:
                entity_id = entity_id_template.format(slugify(key))
                main_entity_details = data.get(main_attribute, FALSE_STR)

                device_attributes = {
                    ATTR_DEVICE_CLASS: DEVICE_CLASS_CONNECTIVITY,
                    ATTR_FRIENDLY_NAME: f'{DEFAULT_NAME} {sensor_type} {key}'
                }

                for data_item_key in data:
                    if data_item_key != main_attribute:
                        value = data.get(data_item_key)
                        attr = get_attributes(data_item_key)

                        name = attr.get(ATTR_NAME, data_item_key)
                        unit_of_measurement = attr.get(ATTR_UNIT_OF_MEASUREMENT)

                        if unit_of_measurement is None:
                            device_attributes[name] = value
                        else:
                            name = name.format(self._unit)

                            device_attributes[name] = (int(value) * BITS_IN_BYTE) / self._unit_size

                if str(main_entity_details).lower() == TRUE_STR:
                    state = STATE_ON
                else:
                    state = STATE_OFF

                current_entity = self._hass.states.get(entity_id)

                device_attributes[EVENT_TIME_CHANGED] = datetime.now().strftime(DEFAULT_DATE_FORMAT)

                if current_entity is not None and current_entity.state == state:
                    entity_attributes = current_entity.attributes
                    device_attributes[EVENT_TIME_CHANGED] = entity_attributes.get(EVENT_TIME_CHANGED)

                self._hass.states.async_set(entity_id, state, device_attributes)

        except Exception as ex:
            error_message = f'Failed to create {key} sensor {sensor_type} with the following data: {data}'

            self.log_exception(ex, error_message)

    def create_unknown_devices_sensor(self, unknown_devices):
        try:
            devices_count = len(unknown_devices)

            entity_id = ENTITY_ID_UNKNOWN_DEVICES
            state = devices_count

            attributes = {}

            if devices_count > 0:
                attributes[STATE_UNKNOWN] = unknown_devices

            self._hass.states.async_set(entity_id, state, attributes)
        except Exception as ex:
            error_message = f'Failed to create unknown device sensor, Data: {unknown_devices}'

            self.log_exception(ex, error_message)

    def create_system_sensor(self, system_state, api_last_update, web_socket_last_update):
        try:
            if system_state is not None:
                attributes = {
                    ATTR_UNIT_OF_MEASUREMENT: ATTR_SECONDS,
                    ATTR_FRIENDLY_NAME: f'{DEFAULT_NAME} {ATTR_SYSTEM_UPTIME}',
                    ATTR_API_LAST_UPDATE: api_last_update,
                    ATTR_WEBSOCKET_LAST_UPDATE: web_socket_last_update
                }

                for key in system_state:
                    if key != UPTIME:
                        attributes[key] = system_state[key]

                entity_id = ENTITY_ID_SYSTEM_UPTIME
                state = system_state.get(UPTIME, 0)

                self._hass.states.async_set(entity_id, state, attributes)
        except Exception as ex:
            error_message = 'Failed to create system sensor'

            self.log_exception(ex, error_message)

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
