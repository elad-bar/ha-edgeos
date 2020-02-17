"""
This component provides support for Home Automation Manager (HAM).
For more details about this component, please refer to the documentation at
https://home-assistant.io/components/edgeos/
"""
import sys
import logging

from homeassistant.helpers import device_registry as dr
from homeassistant.components.device_tracker import ATTR_SOURCE_TYPE, SOURCE_TYPE_ROUTER
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from homeassistant.const import ATTR_FRIENDLY_NAME

from homeassistant.helpers.event import async_call_later, async_track_time_interval
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .EdgeOSData import EdgeOSData
from .const import *

_LOGGER = logging.getLogger(__name__)


class EdgeOSHomeAssistant:
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        self._hass = hass

        self._config_entry = entry
        self._unload_domain = []
        self._load_domain = []
        self._should_reload = False

        self._allowed_interfaces = []
        self._allowed_devices = []
        self._allowed_track_devices = []

        self._unit = entry.data.get(CONF_UNIT, ATTR_BYTE)
        self._unit_size = ALLOWED_UNITS.get(self._unit, BYTE)

        self._remove_async_track_time_api = None
        self._remove_async_track_time_entities = None

        self._entities = {}
        self._domain_loaded = {}

        self._last_update = None

        self._data = EdgeOSData(self._hass, entry.data, self.update)

        for domain in [DOMAIN_SENSOR, DOMAIN_BINARY_SENSOR, DOMAIN_DEVICE_TRACKER]:
            self._entities[domain] = {}
            self.set_domain_entities_state(domain, False)

    async def initialize(self):
        async_call_later(self._hass, 5, self.async_finalize)

    async def async_finalize(self, event_time):
        _LOGGER.debug(f"async_finalize called at {event_time}")

        # Register Service
        self._hass.services.async_register(DOMAIN, 'stop', self.stop)
        self._hass.services.async_register(DOMAIN, 'restart', self.initialize_data)
        self._hass.services.async_register(DOMAIN, 'save_debug_data', self.save_debug_data)
        self._hass.services.async_register(DOMAIN, 'log_events', self.log_events, schema=SERVICE_LOG_EVENTS_SCHEMA)

        self.initialize_data(None)

        self._remove_async_track_time_api = async_track_time_interval(self._hass,
                                                                      self.async_update_api,
                                                                      SCAN_INTERVAL_API)

        self._remove_async_track_time_entities = async_track_time_interval(self._hass,
                                                                           self.async_update_entities,
                                                                           SCAN_INTERVAL_ENTITIES)

    async def async_remove(self):
        _LOGGER.debug(f"async_remove called")

        self.stop(None)

        # Unregister Service
        self._hass.services.async_remove(DOMAIN, 'stop')
        self._hass.services.async_remove(DOMAIN, 'restart')
        self._hass.services.async_remove(DOMAIN, 'save_debug_data')
        self._hass.services.async_remove(DOMAIN, 'log_events')

        if self._remove_async_track_time_api is not None:
            self._remove_async_track_time_api()

        if self._remove_async_track_time_entities is not None:
            self._remove_async_track_time_entities()

        unload = self._hass.config_entries.async_forward_entry_unload

        self._hass.async_create_task(unload(self._config_entry, DOMAIN_BINARY_SENSOR))
        self._hass.async_create_task(unload(self._config_entry, DOMAIN_SENSOR))
        self._hass.async_create_task(unload(self._config_entry, DOMAIN_DEVICE_TRACKER))

    async def async_update_entry(self, entry, clear_all):
        _LOGGER.info(f"async_update_entry: {self._config_entry.options}")

        self._config_entry = entry
        self._last_update = datetime.now()

        options = self._config_entry.options

        if options is not None:
            monitored_interfaces = options.get(CONF_MONITORED_INTERFACES, "").replace(" ", "")
            monitored_devices = options.get(CONF_MONITORED_DEVICES, "").replace(" ", "")
            track_devices = options.get(CONF_TRACK_DEVICES, "").replace(" ", "")

            self._allowed_interfaces = monitored_interfaces.split(",")
            self._allowed_devices = monitored_devices.split(",")
            self._allowed_track_devices = track_devices.split(",")

        self._load_domain = []
        self._unload_domain = []

        if clear_all:
            device_reg = await dr.async_get_registry(self._hass)
            device_reg.async_clear_config_entry(self._config_entry.entry_id)

        for domain in [DOMAIN_SENSOR, DOMAIN_BINARY_SENSOR, DOMAIN_DEVICE_TRACKER]:
            has_entities = self._domain_loaded.get(domain, False)

            if domain not in self._load_domain:
                self._load_domain.append(domain)

            if has_entities and domain not in self._unload_domain:
                self._unload_domain.append(domain)

        if clear_all:
            self._data.update(True)

            await self.discover_all()

        # await self._data.refresh()

    async def async_init_entry(self):
        _LOGGER.debug(f"async_init_entry called")

        await self.async_update_entry(self._config_entry, False)

    async def async_update_api(self, event_time):
        _LOGGER.debug(f'Update API: {event_time}')

        await self._data.refresh()

    async def async_update_entities(self, event_time):
        _LOGGER.debug(f'Update entities: {event_time}')

        await self.discover_all()

    def set_domain_entities_state(self, domain, has_entities):
        self._domain_loaded[domain] = has_entities

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

    def stop(self, service):
        _LOGGER.debug(f'Stop: {service}')

        self._hass.async_create_task(self._data.terminate())

    def initialize_data(self, service):
        _LOGGER.debug(f'Start: {service}')

        self._hass.async_create_task(self._data.initialize(self.async_init_entry))

    def save_debug_data(self, service):
        _LOGGER.debug(f'Save Debug Data: {service}')

        self.store_data()

    def log_events(self, service):
        _LOGGER.debug(f'Log Events: {service}')

        enabled = service.data.get(ATTR_ENABLED, False)

        self._data.log_events(enabled)

    def update(self, interfaces, devices, unknown_devices, system_state, api_last_update, web_socket_last_update):
        try:
            for domain in [DOMAIN_SENSOR, DOMAIN_BINARY_SENSOR, DOMAIN_DEVICE_TRACKER]:
                self._entities[domain] = {}

            self.create_interface_binary_sensors(interfaces)
            self.create_device_binary_sensors(devices)
            self.create_device_trackers(devices)
            self.create_unknown_devices_sensor(unknown_devices)
            self.create_uptime_sensor(system_state, api_last_update, web_socket_last_update)
            self.create_system_status_binary_sensor(system_state, api_last_update, web_socket_last_update)
        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(f'Failed to update, Error: {ex}, Line: {line_number}')

    async def discover_all(self):
        for domain in [DOMAIN_SENSOR, DOMAIN_BINARY_SENSOR, DOMAIN_DEVICE_TRACKER]:
            await self.discover(domain)

    async def discover(self, domain):
        signal = SIGNALS.get(domain)

        if signal is None:
            _LOGGER.error(f"Cannot discover domain {domain}")
            return

        unload = self._hass.config_entries.async_forward_entry_unload
        setup = self._hass.config_entries.async_forward_entry_setup

        entry = self._config_entry
        
        can_unload = domain in self._unload_domain
        can_load = domain in self._load_domain
        can_notify = not can_load and not can_unload

        if can_unload:
            _LOGGER.info(f"Unloading domain {domain}")

            self._hass.async_create_task(unload(entry, domain))
            self._unload_domain.remove(domain)

        if can_load:
            _LOGGER.info(f"Loading domain {domain}")

            self._hass.async_create_task(setup(entry, domain))
            self._load_domain.remove(domain)

        if can_notify:
            async_dispatcher_send(self._hass, signal)

    def create_device_trackers(self, devices):
        try:
            for hostname in devices:
                host_data = devices.get(hostname, {})

                self.create_device_tracker(hostname, host_data)

        except Exception as ex:
            self.log_exception(ex, 'Failed to updated device trackers')

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
                            name = name.format(self._unit)

                            attributes[name] = (int(value) * BITS_IN_BYTE) / self._unit_size

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
                    ENTITY_ICON: ICONS[sensor_type]
                }

                self.set_entity(DOMAIN_BINARY_SENSOR, entity_name, entity)

        except Exception as ex:
            self.log_exception(ex, f'Failed to create {key} sensor {sensor_type} with the following data: {data}')

    def create_unknown_devices_sensor(self, unknown_devices):
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
                ENTITY_ICON: "mdi:help-rhombus"
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
                ENTITY_ICON: "mdi:timer-sand"
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
                ENTITY_ICON: CONNECTED_ICONS[is_alive]
            }

            self.set_entity(DOMAIN_BINARY_SENSOR, entity_name, entity)
        except Exception as ex:
            self.log_exception(ex, 'Failed to create system status binary sensor')

    def create_device_tracker(self, host, data):
        try:
            allowed_items = self._allowed_track_devices
            if host in allowed_items:
                entity_name = f'{DEFAULT_NAME} {host}'

                state = self._data.is_device_online(host)

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
                    ENTITY_ATTRIBUTES: attributes
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

    def store_data(self):
        try:
            path = self._hass.config.path(EDGEOS_DATA_LOG)

            with open(path, 'w+') as out:
                out.write(str(self._data.data))

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(f'Failed to log EdgeOS data, Error: {ex}, Line: {line_number}')


def _get_ha_data(hass, name) -> EdgeOSHomeAssistant:
    ha = hass.data[DATA_EDGEOS]
    ha_data = None

    if ha is not None:
        ha_data = ha.get(name)

    return ha_data
