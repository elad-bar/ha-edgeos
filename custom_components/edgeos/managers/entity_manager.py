import logging
import sys
from typing import Dict, List, Optional

from homeassistant.components.device_tracker import ATTR_SOURCE_TYPE, SOURCE_TYPE_ROUTER
from homeassistant.const import ATTR_FRIENDLY_NAME, CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_registry import EntityRegistry

from ..helpers.const import *
from ..managers.data_manager import EdgeOSData
from ..models.config_data import ConfigData
from ..models.entity_data import EntityData

_LOGGER = logging.getLogger(__name__)


class EntityManager:
    hass: HomeAssistant
    ha = None
    entities: dict
    domain_component_manager: dict

    def __init__(self, hass, ha):
        self.hass = hass
        self.ha = ha
        self.domain_component_manager = {}
        self.entities = {}

    @property
    def entity_registry(self) -> EntityRegistry:
        return self.ha.entity_registry

    @property
    def config_data(self) -> ConfigData:
        return self.ha.config_data

    @property
    def data_manager(self) -> EdgeOSData:
        return self.ha.data_manager

    @property
    def system_data(self):
        return self.data_manager.system_data

    def set_domain_component(self, domain, async_add_entities, component):
        self.domain_component_manager[domain] = {
            "async_add_entities": async_add_entities,
            "component": component,
        }

    def is_device_name_in_use(self, device_name):
        result = False

        for entity in self.get_all_entities():
            if entity.device_name == device_name:
                result = True
                break

        return result

    def get_all_entities(self) -> List[EntityData]:
        entities = []
        for domain in self.entities:
            for name in self.entities[domain]:
                entity = self.entities[domain][name]

                entities.append(entity)

        return entities

    def check_domain(self, domain):
        if domain not in self.entities:
            self.entities[domain] = {}

    def get_entities(self, domain) -> Dict[str, EntityData]:
        self.check_domain(domain)

        return self.entities[domain]

    def get_entity(self, domain, name) -> Optional[EntityData]:
        entities = self.get_entities(domain)
        entity = entities.get(name)

        return entity

    def delete_entity(self, domain, name):
        if domain in self.entities and name in self.entities[domain]:
            del self.entities[domain][name]

    def set_entity(self, domain, name, data: EntityData):
        try:
            self.check_domain(domain)

            self.entities[domain][name] = data
        except Exception as ex:
            self.log_exception(
                ex, f"Failed to set_entity, domain: {domain}, name: {name}"
            )

    def create_components(self):
        system_state = self.system_data.get(SYSTEM_STATS_KEY)
        api_last_update = self.system_data.get(ATTR_API_LAST_UPDATE)
        web_socket_last_update = self.system_data.get(ATTR_WEB_SOCKET_LAST_UPDATE)

        self.create_interface_binary_sensors()
        self.create_device_binary_sensors()
        self.create_device_trackers()
        self.create_unknown_devices_sensor()
        self.create_uptime_sensor(system_state, api_last_update, web_socket_last_update)
        self.create_system_status_binary_sensor(
            system_state, api_last_update, web_socket_last_update
        )

    def update(self):
        self.hass.async_create_task(self._async_update())

    async def _async_update(self):
        step = "Mark as ignore"
        try:
            entities_to_delete = []

            for entity in self.get_all_entities():
                entities_to_delete.append(entity.unique_id)

            step = "Create components"

            self.create_components()

            step = "Start updating"

            for domain in SIGNALS:
                step = f"Start updating domain {domain}"

                entities_to_add = []
                domain_component_manager = self.domain_component_manager[domain]
                domain_component = domain_component_manager["component"]
                async_add_entities = domain_component_manager["async_add_entities"]

                entities = dict(self.get_entities(domain))

                for entity_key in entities:
                    step = f"Start updating {domain} -> {entity_key}"

                    entity = entities[entity_key]

                    entity_id = self.entity_registry.async_get_entity_id(
                        domain, DOMAIN, entity.unique_id
                    )

                    if entity.status == ENTITY_STATUS_CREATED:
                        if entity.unique_id in entities_to_delete:
                            entities_to_delete.remove(entity.unique_id)

                        step = f"Mark as created - {domain} -> {entity_key}"

                        entity_component = domain_component(
                            self.hass, self.config_data.name, entity
                        )

                        if entity_id is not None:
                            entity_component.entity_id = entity_id

                            state = self.hass.states.get(entity_id)

                            if state is None:
                                restored = True
                            else:
                                restored = state.attributes.get("restored", False)

                                if restored:
                                    _LOGGER.info(
                                        f"Entity {entity.name} restored | {entity_id}"
                                    )

                            if restored:
                                entity_item = self.entity_registry.async_get(entity_id)

                                if entity_item is None or not entity_item.disabled:
                                    entities_to_add.append(entity_component)
                        else:
                            entities_to_add.append(entity_component)

                        entity.status = ENTITY_STATUS_READY

                step = f"Add entities to {domain}"

                if len(entities_to_add) > 0:
                    async_add_entities(entities_to_add, True)

            if len(entities_to_delete) > 0:
                _LOGGER.info(f"Following items will be deleted: {entities_to_delete}")

                for domain in SIGNALS:
                    entities = dict(self.get_entities(domain))

                    for entity_key in entities:
                        entity = entities[entity_key]
                        if entity.unique_id in entities_to_delete:
                            await self.ha.delete_entity(domain, entity.name)

        except Exception as ex:
            self.log_exception(ex, f"Failed to update, step: {step}")

    def create_device_trackers(self):
        try:
            devices = self.system_data.get(STATIC_DEVICES_KEY)

            for hostname in devices:
                host_data = devices.get(hostname, {})

                self.create_device_tracker(hostname, host_data)

        except Exception as ex:
            self.log_exception(ex, "Failed to updated device trackers")

    def create_device_binary_sensors(self):
        try:
            devices = self.system_data.get(STATIC_DEVICES_KEY)

            for hostname in devices:
                host_data = devices.get(hostname, {})

                self.create_device_binary_sensor(hostname, host_data)

        except Exception as ex:
            self.log_exception(ex, "Failed to updated devices")

    def create_interface_binary_sensors(self):
        try:
            interfaces = self.system_data.get(INTERFACES_KEY)

            for interface in interfaces:
                interface_data = interfaces.get(interface)

                self.create_interface_binary_sensor(interface, interface_data)

        except Exception as ex:
            self.log_exception(ex, f"Failed to update {INTERFACES_KEY}")

    def create_interface_binary_sensor(self, key, data):
        self.create_binary_sensor(
            key,
            data,
            self.config_data.monitored_interfaces,
            SENSOR_TYPE_INTERFACE,
            LINK_UP,
            self.get_interface_attributes,
        )

    def create_device_binary_sensor(self, key, data):
        self.create_binary_sensor(
            key,
            data,
            self.config_data.monitored_devices,
            SENSOR_TYPE_DEVICE,
            CONNECTED,
            self.get_device_attributes,
        )

    def create_binary_sensor(
        self, key, data, allowed_items, sensor_type, main_attribute, get_attributes
    ):
        try:
            if key in allowed_items:
                entity_name = f"{DEFAULT_NAME} {sensor_type} {key}"

                main_entity_details = data.get(main_attribute, FALSE_STR)

                attributes = {
                    ATTR_DEVICE_CLASS: DEVICE_CLASS_CONNECTIVITY,
                    ATTR_FRIENDLY_NAME: entity_name,
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
                            name = name.format(self.config_data.unit)

                            attributes[name] = (
                                int(value) * BITS_IN_BYTE
                            ) / self.config_data.unit_size

                is_on = str(main_entity_details).lower() == TRUE_STR

                current_entity = self.get_entity(DOMAIN_BINARY_SENSOR, entity_name)

                attributes[ATTR_LAST_CHANGED] = datetime.now().strftime(
                    DEFAULT_DATE_FORMAT
                )

                if current_entity is not None and current_entity.state == is_on:
                    entity_attributes = current_entity.attributes
                    attributes[ATTR_LAST_CHANGED] = entity_attributes.get(
                        ATTR_LAST_CHANGED
                    )

                icon = ICONS[sensor_type]

                self.create_entity(
                    DOMAIN_BINARY_SENSOR, entity_name, is_on, attributes, icon
                )

        except Exception as ex:
            self.log_exception(
                ex,
                f"Failed to create {key} sensor {sensor_type} with the following data: {data}",
            )

    def create_unknown_devices_sensor(self):
        unknown_devices = self.system_data.get(UNKNOWN_DEVICES_KEY)

        try:
            entity_name = f"{DEFAULT_NAME} Unknown Devices"

            state = len(unknown_devices)
            if state < 1:
                unknown_devices = None

            attributes = {
                ATTR_FRIENDLY_NAME: entity_name,
                ATTR_UNKNOWN_DEVICES: unknown_devices,
            }

            self.create_entity(
                DOMAIN_SENSOR, entity_name, state, attributes, "mdi:help-rhombus"
            )
        except Exception as ex:
            self.log_exception(
                ex, f"Failed to create unknown device sensor, Data: {unknown_devices}"
            )

    def create_uptime_sensor(
        self, system_state, api_last_update, web_socket_last_update
    ):
        try:
            entity_name = f"{DEFAULT_NAME} {ATTR_SYSTEM_UPTIME}"

            state = system_state.get(UPTIME, 0)
            attributes = {}

            if system_state is not None:
                attributes = {
                    ATTR_UNIT_OF_MEASUREMENT: ATTR_SECONDS,
                    ATTR_FRIENDLY_NAME: entity_name,
                    ATTR_API_LAST_UPDATE: api_last_update.strftime(DEFAULT_DATE_FORMAT),
                    ATTR_WEB_SOCKET_LAST_UPDATE: web_socket_last_update.strftime(
                        DEFAULT_DATE_FORMAT
                    ),
                }

                for key in system_state:
                    if key != UPTIME:
                        attributes[key] = system_state[key]

            self.create_entity(
                DOMAIN_SENSOR, entity_name, state, attributes, "mdi:timer-sand"
            )
        except Exception as ex:
            self.log_exception(ex, "Failed to create system sensor")

    def create_system_status_binary_sensor(
        self, system_state, api_last_update, web_socket_last_update
    ):
        try:
            entity_name = f"{DEFAULT_NAME} {ATTR_SYSTEM_STATUS}"

            attributes = {}
            is_alive = False

            if system_state is not None:
                attributes = {
                    ATTR_DEVICE_CLASS: DEVICE_CLASS_CONNECTIVITY,
                    ATTR_FRIENDLY_NAME: entity_name,
                    ATTR_API_LAST_UPDATE: api_last_update.strftime(DEFAULT_DATE_FORMAT),
                    ATTR_WEB_SOCKET_LAST_UPDATE: web_socket_last_update.strftime(
                        DEFAULT_DATE_FORMAT
                    ),
                }

                for key in system_state:
                    if key != IS_ALIVE:
                        attributes[key] = system_state[key]

                is_alive = system_state.get(IS_ALIVE, False)

            icon = CONNECTED_ICONS[is_alive]

            self.create_entity(
                DOMAIN_BINARY_SENSOR, entity_name, is_alive, attributes, icon
            )
        except Exception as ex:
            self.log_exception(ex, "Failed to create system status binary sensor")

    def create_device_tracker(self, host, data):
        try:
            allowed_items = self.config_data.device_trackers

            if host in allowed_items:
                entity_name = f"{DEFAULT_NAME} {host}"

                state = self.data_manager.is_device_online(host)

                attributes = {ATTR_SOURCE_TYPE: SOURCE_TYPE_ROUTER, CONF_HOST: host}

                for data_item_key in data:
                    value = data.get(data_item_key)
                    attr = self.get_device_attributes(data_item_key)

                    name = attr.get(ATTR_NAME, data_item_key)

                    if ATTR_UNIT_OF_MEASUREMENT not in attr:
                        attributes[name] = value

                self.create_entity(
                    DOMAIN_DEVICE_TRACKER, entity_name, state, attributes
                )

        except Exception as ex:
            self.log_exception(
                ex,
                f"Failed to create {host} device tracker with the following data: {data}",
            )

    def create_entity(
        self,
        domain: str,
        name: str,
        state: int,
        attributes: dict,
        icon: Optional[str] = None,
    ):
        entity = EntityData()

        entity.name = name
        entity.state = state
        entity.attributes = attributes
        entity.device_name = DEFAULT_NAME
        entity.unique_id = f"{DEFAULT_NAME}-{domain}-{name}"

        if icon is not None:
            entity.icon = icon

        self.set_entity(domain, name, entity)

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

        _LOGGER.error(f"{message}, Error: {str(ex)}, Line: {line_number}")
