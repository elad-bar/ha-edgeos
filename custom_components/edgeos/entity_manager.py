import sys
import logging

from homeassistant.components.device_tracker import ATTR_SOURCE_TYPE, SOURCE_TYPE_ROUTER

from homeassistant.const import ATTR_FRIENDLY_NAME

from .EdgeOSData import EdgeOSData
from .const import *

_LOGGER = logging.getLogger(__name__)


def _get_camera_binary_sensor_key(topic, event_type):
    key = f"{topic}_{event_type}".lower()

    return key


class EntityManager:
    def __init__(self, hass, ha):
        self._hass = hass
        self._ha = ha

        self._entities = {}
        self._entry_loaded_state = {}
        self._domain_states: dict = {}

        self._allowed_interfaces = []
        self._allowed_devices = []
        self._allowed_track_devices = []

        self._data_manager: EdgeOSData = self._ha.data_manager

        for domain in SIGNALS:
            self.clear_entities(domain)
            self.set_domain_state(domain, DOMAIN_LOAD, False)
            self.set_domain_state(domain, DOMAIN_UNLOAD, False)
            self.set_entry_loaded_state(domain, False)

    @property
    def system_data(self):
        return self._data_manager.system_data

    def update_options(self, options):
        if options is None:
            options = {}

        monitored_interfaces = options.get(CONF_MONITORED_INTERFACES, "").replace(" ", "")
        monitored_devices = options.get(CONF_MONITORED_DEVICES, "").replace(" ", "")
        track_devices = options.get(CONF_TRACK_DEVICES, "").replace(" ", "")

        self._allowed_interfaces = monitored_interfaces.split(",")
        self._allowed_devices = monitored_devices.split(",")
        self._allowed_track_devices = track_devices.split(",")

    def set_entry_loaded_state(self, domain, has_entities):
        self._entry_loaded_state[domain] = has_entities

    def get_entry_loaded_state(self, domain):
        return self._entry_loaded_state.get(domain, False)

    def clear_entities(self, domain):
        self._entities[domain] = {}

    def get_entities(self, domain):
        return self._entities.get(domain, {})

    def get_entity(self, domain, name):
        entities = self.get_entities(domain)
        entity = {}
        if entities is not None:
            entity = entities.get(name, {})

        return entity

    def set_entity(self, domain, name, data):
        entities = self._entities.get(domain)

        if entities is None:
            self._entities[domain] = {}

            entities = self._entities.get(domain)

        entities[name] = data

    def update(self):
        system_state = self.system_data.get(SYSTEM_STATS_KEY)
        api_last_update = self.system_data.get(ATTR_API_LAST_UPDATE)
        web_socket_last_update = self.system_data.get(ATTR_WEB_SOCKET_LAST_UPDATE)

        previous_keys = {}
        for domain in SIGNALS:
            previous_keys[domain] = ','.join(self.get_entities(domain).keys())

            self.clear_entities(domain)

        self.create_interface_binary_sensors()
        self.create_device_binary_sensors()
        self.create_device_trackers()
        self.create_unknown_devices_sensor()
        self.create_uptime_sensor(system_state, api_last_update, web_socket_last_update)
        self.create_system_status_binary_sensor(system_state, api_last_update, web_socket_last_update)

        for domain in SIGNALS:
            domain_keys = self.get_entities(domain).keys()
            previous_domain_keys = previous_keys[domain]
            entry_loaded_state = self.get_entry_loaded_state(domain)

            if len(domain_keys) > 0:
                current_keys = ','.join(domain_keys)

                if current_keys != previous_domain_keys:
                    self.set_domain_state(domain, DOMAIN_LOAD, True)

                    if len(previous_domain_keys) > 0:
                        self.set_domain_state(domain, DOMAIN_UNLOAD, entry_loaded_state)
            else:
                if len(previous_domain_keys) > 0:
                    self.set_domain_state(domain, DOMAIN_UNLOAD, entry_loaded_state)

    def get_domain_state(self, domain, key):
        if domain not in self._domain_states:
            self._domain_states[domain] = {}

        return self._domain_states[domain].get(key, False)

    def set_domain_state(self, domain, key, state):
        if domain not in self._domain_states:
            self._domain_states[domain] = {}

        self._domain_states[domain][key] = state

    def clear_domain_states(self):
        for domain in SIGNALS:
            self.set_domain_state(domain, DOMAIN_LOAD, False)
            self.set_domain_state(domain, DOMAIN_UNLOAD, False)

    def get_domain_states(self):
        return self._domain_states

    def create_device_trackers(self):
        try:
            devices = self.system_data.get(STATIC_DEVICES_KEY)

            for hostname in devices:
                host_data = devices.get(hostname, {})

                self.create_device_tracker(hostname, host_data)

        except Exception as ex:
            self.log_exception(ex, 'Failed to updated device trackers')

    def create_device_binary_sensors(self):
        try:
            devices = self.system_data.get(STATIC_DEVICES_KEY)

            for hostname in devices:
                host_data = devices.get(hostname, {})

                self.create_device_binary_sensor(hostname, host_data)

        except Exception as ex:
            self.log_exception(ex, 'Failed to updated devices')

    def create_interface_binary_sensors(self):
        try:
            interfaces = self.system_data.get(INTERFACES_KEY)

            for interface in interfaces:
                interface_data = interfaces.get(interface)

                self.create_interface_binary_sensor(interface, interface_data)

        except Exception as ex:
            self.log_exception(ex, f'Failed to update {INTERFACES_KEY}')

    def create_interface_binary_sensor(self, key, data):
        self.create_binary_sensor(key, data, self._allowed_interfaces, SENSOR_TYPE_INTERFACE,
                                  LINK_UP, self.get_interface_attributes)

    def create_device_binary_sensor(self, key, data):
        self.create_binary_sensor(key, data, self._allowed_devices, SENSOR_TYPE_DEVICE,
                                  CONNECTED, self.get_device_attributes)

    def create_binary_sensor(self, key, data, allowed_items, sensor_type, main_attribute, get_attributes):
        try:
            if key in allowed_items:
                entity_name = f'{DEFAULT_NAME} {sensor_type} {key}'

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
                            name = name.format(self._ha.unit)

                            attributes[name] = (int(value) * BITS_IN_BYTE) / self._ha.unit_size

                is_on = str(main_entity_details).lower() == TRUE_STR

                entities = self.get_entities(DOMAIN_BINARY_SENSOR)
                current_entity = entities.get(entity_name)

                attributes[ATTR_LAST_CHANGED] = datetime.now().strftime(DEFAULT_DATE_FORMAT)

                if current_entity is not None and current_entity.get(ENTITY_STATE) == is_on:
                    entity_attributes = current_entity.get(ENTITY_ATTRIBUTES, {})
                    attributes[ATTR_LAST_CHANGED] = entity_attributes.get(ATTR_LAST_CHANGED)

                entity = {
                    ENTITY_NAME: entity_name,
                    ENTITY_STATE: is_on,
                    ENTITY_ATTRIBUTES: attributes,
                    ENTITY_ICON: ICONS[sensor_type],
                    ENTITY_DEVICE_NAME: DEFAULT_NAME
                }

                self.set_entity(DOMAIN_BINARY_SENSOR, entity_name, entity)

        except Exception as ex:
            self.log_exception(ex, f'Failed to create {key} sensor {sensor_type} with the following data: {data}')

    def create_unknown_devices_sensor(self):
        unknown_devices = self.system_data.get(UNKNOWN_DEVICES_KEY)

        try:
            entity_name = f"{DEFAULT_NAME} Unknown Devices"

            state = len(unknown_devices)
            if state < 1:
                unknown_devices = None

            attributes = {
                ATTR_FRIENDLY_NAME: entity_name,
                ATTR_UNKNOWN_DEVICES:  unknown_devices
            }

            entity = {
                ENTITY_NAME: entity_name,
                ENTITY_STATE: state,
                ENTITY_ATTRIBUTES: attributes,
                ENTITY_ICON: "mdi:help-rhombus",
                ENTITY_DEVICE_NAME: DEFAULT_NAME
            }

            self.set_entity(DOMAIN_SENSOR, entity_name, entity)
        except Exception as ex:
            self.log_exception(ex, f'Failed to create unknown device sensor, Data: {unknown_devices}')

    def create_uptime_sensor(self, system_state, api_last_update, web_socket_last_update):
        try:
            entity_name = f'{DEFAULT_NAME} {ATTR_SYSTEM_UPTIME}'

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

            entity = {
                ENTITY_NAME: entity_name,
                ENTITY_STATE: state,
                ENTITY_ATTRIBUTES: attributes,
                ENTITY_ICON: "mdi:timer-sand",
                ENTITY_DEVICE_NAME: DEFAULT_NAME
            }

            self.set_entity(DOMAIN_SENSOR, entity_name, entity)
        except Exception as ex:
            self.log_exception(ex, 'Failed to create system sensor')

    def create_system_status_binary_sensor(self, system_state, api_last_update, web_socket_last_update):
        try:
            entity_name = f'{DEFAULT_NAME} {ATTR_SYSTEM_STATUS}'

            attributes = {}
            is_alive = False

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

            entity = {
                ENTITY_NAME: entity_name,
                ENTITY_STATE: is_alive,
                ENTITY_ATTRIBUTES: attributes,
                ENTITY_ICON: CONNECTED_ICONS[is_alive],
                ENTITY_DEVICE_NAME: DEFAULT_NAME
            }

            self.set_entity(DOMAIN_BINARY_SENSOR, entity_name, entity)
        except Exception as ex:
            self.log_exception(ex, 'Failed to create system status binary sensor')

    def create_device_tracker(self, host, data):
        try:
            allowed_items = self._allowed_track_devices

            if host in allowed_items:
                entity_name = f'{DEFAULT_NAME} {host}'

                state = self._data_manager.is_device_online(host)

                attributes = {
                    ATTR_SOURCE_TYPE: SOURCE_TYPE_ROUTER,
                    CONF_HOST: host
                }

                for data_item_key in data:
                    value = data.get(data_item_key)
                    attr = self.get_device_attributes(data_item_key)

                    name = attr.get(ATTR_NAME, data_item_key)

                    if ATTR_UNIT_OF_MEASUREMENT not in attr:
                        attributes[name] = value

                entity = {
                    ENTITY_NAME: entity_name,
                    ENTITY_STATE: state,
                    ENTITY_ATTRIBUTES: attributes,
                    ENTITY_DEVICE_NAME: DEFAULT_NAME
                }

                self.set_entity(DOMAIN_DEVICE_TRACKER, entity_name, entity)

        except Exception as ex:
            self.log_exception(ex, f'Failed to create {host} device tracker with the following data: {data}')

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
