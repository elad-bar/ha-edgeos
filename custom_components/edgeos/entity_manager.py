import sys
import logging

from homeassistant.components.device_tracker import ATTR_SOURCE_TYPE, SOURCE_TYPE_ROUTER

from homeassistant.const import ATTR_FRIENDLY_NAME
from homeassistant.helpers.entity_registry import EntityRegistry

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

        self._allowed_interfaces = []
        self._allowed_devices = []
        self._allowed_track_devices = []

        self._options = None

        self._data_manager: EdgeOSData = self._ha.data_manager
        self._domain_component_manager: dict = {}

        for domain in SIGNALS:
            self.clear_entities(domain)

    @property
    def system_data(self):
        return self._data_manager.system_data

    @property
    def entity_registry(self) -> EntityRegistry:
        return self._ha.entity_registry

    def set_domain_component(self, domain, async_add_entities, component):
        self._domain_component_manager[domain] = {
            "async_add_entities": async_add_entities,
            "component": component
        }

    def get_option(self, option_key):
        result = []
        data = self._options.get(option_key)

        if data is not None:
            if isinstance(data, list):
                result = data
            else:
                clean_data = data.replace(" ", "")
                result = clean_data.split(",")

        return result

    def update_options(self, options):
        if options is None:
            options = {}

        self._options = options

        self._allowed_interfaces = self.get_option(CONF_MONITORED_INTERFACES)
        self._allowed_devices = self.get_option(CONF_MONITORED_DEVICES)
        self._allowed_track_devices = self.get_option(CONF_TRACK_DEVICES)

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

    def get_entity_status(self, domain, name):
        entity = self.get_entity(domain, name)
        status = entity.get(ENTITY_STATUS)

        return status

    def set_entity_status(self, domain, name, status):
        if domain in self._entities and name in self._entities[domain]:
            self._entities[domain][name][ENTITY_STATUS] = status

    def delete_entity(self, domain, name):
        if domain in self._entities and name in self._entities[domain]:
            del self._entities[domain][name]

    def set_entity(self, domain, name, data):
        if domain not in self._entities:
            self._entities[domain] = {}

        status = self.get_entity_status(domain, name)

        self._entities[domain][name] = data

        if status == ENTITY_STATUS_EMPTY:
            status = ENTITY_STATUS_CREATED
        else:
            status = ENTITY_STATUS_MODIFIED

        self.set_entity_status(domain, name, status)

    def create_components(self):
        system_state = self.system_data.get(SYSTEM_STATS_KEY)
        api_last_update = self.system_data.get(ATTR_API_LAST_UPDATE)
        web_socket_last_update = self.system_data.get(ATTR_WEB_SOCKET_LAST_UPDATE)

        self.create_interface_binary_sensors()
        self.create_device_binary_sensors()
        self.create_device_trackers()
        self.create_unknown_devices_sensor()
        self.create_uptime_sensor(system_state, api_last_update, web_socket_last_update)
        self.create_system_status_binary_sensor(system_state, api_last_update, web_socket_last_update)

    def update(self):
        try:
            for domain in SIGNALS:
                for entity_key in self.get_entities(domain):
                    self.set_entity_status(domain, entity_key, ENTITY_STATUS_IGNORE)

            self.create_components()

            for domain in SIGNALS:
                entities_to_add = []
                domain_component_manager = self._domain_component_manager[domain]
                domain_component = domain_component_manager["component"]
                async_add_entities = domain_component_manager["async_add_entities"]

                entities = dict(self.get_entities(domain))

                for entity_key in entities:
                    entity = entities[entity_key]
                    status = self.get_entity_status(domain, entity_key)
                    name = entity.get(ENTITY_NAME)
                    unique_id = f"{DEFAULT_NAME}-{domain}-{name}"

                    entity_id = self.entity_registry.async_get_entity_id(domain, DOMAIN, unique_id)

                    if status == ENTITY_STATUS_IGNORE:
                        self.set_entity_status(domain, entity_key, ENTITY_STATUS_CANCELLED)

                        self.entity_registry.async_remove(entity_id)

                        self.delete_entity(domain, entity_key)
                    elif status == ENTITY_STATUS_CREATED:
                        entity_component = domain_component(self._hass, self._ha, entity)

                        if not entity_id:
                            entity_component.entity_id = entity_id

                        entities_to_add.append(entity_component)

                if len(entities_to_add) > 0:
                    async_add_entities(entities_to_add, True)

        except Exception as ex:
            self.log_exception(ex, 'Failed to update')

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
