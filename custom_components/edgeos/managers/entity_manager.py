from __future__ import annotations

from datetime import date
import logging
import sys
from typing import Dict, List, Optional

from homeassistant.components.device_tracker import ATTR_SOURCE_TYPE, SOURCE_TYPE_ROUTER
from homeassistant.const import ATTR_FRIENDLY_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_registry import EntityRegistry
from homeassistant.helpers.typing import StateType

from ..helpers.const import *
from ..managers.data_manager import EdgeOSData
from ..models.config_data import ConfigData
from ..models.entity_data import EntityData
from .configuration_manager import ConfigManager

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
    def config_manager(self) -> ConfigManager:
        return self.ha.config_manager

    @property
    def config_data(self) -> ConfigData:
        return self.ha.config_data

    @property
    def data_manager(self) -> EdgeOSData:
        return self.ha.data_manager

    @property
    def integration_title(self) -> str:
        return self.config_manager.config_entry.title

    @property
    def system_data(self):
        return self.data_manager.system_data

    def set_domain_component(self, domain, async_add_entities, component):
        if domain in self.domain_component_manager:
            _LOGGER.warning(f'Domain {domain} already set up')
        else:
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

    def get_all_entities(self) -> list[EntityData]:
        entities = []
        for domain in self.entities:
            for name in self.entities[domain]:
                entity = self.entities[domain][name]

                entities.append(entity)

        return entities

    def check_domain(self, domain):
        if domain not in self.entities:
            self.entities[domain] = {}

    def get_entities(self, domain) -> dict[str, EntityData]:
        self.check_domain(domain)

        return self.entities[domain]

    def get_entity(self, domain, name) -> EntityData | None:
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
        for entity_type in STATS_MAPS.keys():
            self.create_entities(entity_type)

        self.create_device_trackers()
        self.create_unknown_devices_sensor()
        self.create_system_status_binary_sensor()

    def update(self):
        self.hass.async_create_task(self._async_update())

    async def _async_update(self):
        step = "Mark as ignore"
        try:
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
                        entity_item = self.entity_registry.async_get(entity_id)

                        step = f"Mark as created - {domain} -> {entity_key}"

                        entity_component = domain_component(
                            self.hass, self.config_manager.config_entry.entry_id, entity
                        )

                        if entity_id is not None:
                            entity_component.entity_id = entity_id

                            state = self.hass.states.get(entity_id)

                            if state is None:
                                restored = True
                            else:
                                restored = state.attributes.get("restored", False)

                                if restored:
                                    self.hass.states.async_remove(entity_id)

                                    _LOGGER.info(
                                        f"Entity {entity.name} restored | {entity_id}"
                                    )

                            if restored:
                                if entity_item is None or not entity_item.disabled:
                                    entities_to_add.append(entity_component)
                        else:
                            entities_to_add.append(entity_component)

                        entity.status = ENTITY_STATUS_READY

                        if entity_item is not None:
                            entity.disabled = entity_item.disabled

                step = f"Add entities to {domain}"

                if len(entities_to_add) > 0:
                    async_add_entities(entities_to_add, True)

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

    def create_entities(self, entity_type):
        _LOGGER.debug(f"Creating entities for '{entity_type}'")

        all_data = self.system_data.get(entity_type)
        monitored_data = self._get_monitored_data(entity_type)
        stats_keys = STATS_MAPS[entity_type]

        _LOGGER.debug(f"Entities for '{entity_type}' including items: {monitored_data}")

        for item in monitored_data:
            data = all_data.get(item)

            if data is None:
                _LOGGER.info(f"{entity_type} '{item}' was not found, please update the integration's settings")
            else:
                name = data.get(ATTR_NAME, item)

                self.create_main_binary_sensor(item, name, data, entity_type)

                for stats_key in stats_keys:
                    self.create_stats_sensor(item, name, data, stats_key, entity_type)

    def create_main_binary_sensor(self, item, name, data, data_type):
        sensor_type = SENSOR_TYPES[data_type]

        try:
            entity_name = f"{self.integration_title} {sensor_type} {name}"
            icon = ICONS[sensor_type]
            attributes = self._get_attributes(data_type, data)

            attributes[ATTR_FRIENDLY_NAME] = entity_name

            state = data.get(LINK_CONNECTED, FALSE_STR)

            is_on = str(state).lower() == TRUE_STR

            self.create_binary_sensor_entity(
                entity_name, is_on, attributes, BinarySensorDeviceClass.CONNECTIVITY, icon
            )

        except Exception as ex:
            self.log_exception(
                ex,
                f"Failed to create {sensor_type}'s main binary sensor for '{item}', data: {data}",
            )

    def create_stats_sensor(self, item, name, data, stats_key, data_type):
        sensor_type = SENSOR_TYPES[data_type]

        try:
            stats_map = STATS_MAPS[data_type]
            stats_name = stats_key.capitalize()
            unit_of_measurement = UNIT_PACKETS
            value = data.get(stats_key)
            value_factor = 1
            state_class = stats_map[stats_key]
            icon = ICONS[sensor_type]

            if "_" in stats_key:
                stats_parts = stats_key.split("_")
                stats_prefix = stats_parts[0]
                unit_of_measurement = stats_parts[1].capitalize()
                stats_direction = STATS_DIRECTION[stats_prefix]

                if unit_of_measurement.lower() == UNIT_DROPPED_PACKETS.lower():
                    stats_name = f"{UNIT_DROPPED_PACKETS} {UNIT_PACKETS} {stats_direction}"
                    unit_of_measurement = UNIT_PACKETS

                elif unit_of_measurement.lower() in [UNIT_BPS.lower(), UNIT_RATE.lower()]:
                    stats_name = f"{UNIT_RATE} {stats_direction}"
                    unit_of_measurement = f"{self.config_data.unit}/ps"
                    value_factor = self.config_data.unit_size

                elif unit_of_measurement.lower() == UNIT_BYTES.lower():
                    stats_name = f"{UNIT_TRAFFIC} {stats_direction}"
                    unit_of_measurement = self.config_data.unit
                    value_factor = self.config_data.unit_size

                else:
                    stats_name = f"{unit_of_measurement.capitalize()} {stats_direction}"

            if value is not None and value_factor is not None and value_factor > 1:
                value = float(float(value) / float(value_factor))

            entity_name = f"{self.integration_title} {sensor_type} {name} {stats_name}"

            attributes = {
                ATTR_FRIENDLY_NAME: entity_name,
                ATTR_UNIT_OF_MEASUREMENT: unit_of_measurement
            }

            self.create_sensor_entity(
                entity_name, value, attributes, state_class, icon
            )

        except Exception as ex:
            self.log_exception(
                ex,
                f"Failed to create {sensor_type}'s '{stats_key}' sensor for '{item}', data: {data}",
            )

    def create_unknown_devices_sensor(self):
        unknown_devices = self.system_data.get(UNKNOWN_DEVICES_KEY)

        try:
            entity_name = f"{self.integration_title} Unknown Devices"

            state = len(unknown_devices)
            if state < 1:
                unknown_devices = None

            attributes = {
                ATTR_FRIENDLY_NAME: entity_name,
                ATTR_UNKNOWN_DEVICES: unknown_devices,
                ATTR_UNIT_OF_MEASUREMENT: UNIT_DEVICES
            }

            self.create_sensor_entity(
                entity_name, state, attributes, SensorStateClass.MEASUREMENT, "mdi:help-rhombus"
            )
        except Exception as ex:
            self.log_exception(
                ex, f"Failed to create unknown device sensor, Data: {unknown_devices}"
            )

    def create_system_status_binary_sensor(self):
        try:
            system_state = self.system_data.get(SYSTEM_STATS_KEY)
            api_last_update = self.system_data.get(ATTR_API_LAST_UPDATE)
            web_socket_last_update = self.system_data.get(ATTR_WEB_SOCKET_LAST_UPDATE)
            messages_received = self.system_data.get(ATTR_WEB_SOCKET_MESSAGES_RECEIVED)
            messages_ignored = self.system_data.get(ATTR_WEB_SOCKET_MESSAGES_IGNORED)
            messages_handled_percentage = self.system_data.get(ATTR_WEB_SOCKET_MESSAGES_HANDLED_PERCENTAGE)

            entity_name = f"{self.integration_title} {ATTR_SYSTEM_STATUS}"

            attributes = {}
            is_alive = False

            if system_state is not None:
                attributes = {
                    UPTIME: system_state.get(UPTIME, 0),
                    ATTR_FRIENDLY_NAME: entity_name,
                    ATTR_API_LAST_UPDATE: api_last_update.strftime(DEFAULT_DATE_FORMAT),
                    ATTR_WEB_SOCKET_LAST_UPDATE: web_socket_last_update.strftime(
                        DEFAULT_DATE_FORMAT
                    ),
                    ATTR_WEB_SOCKET_MESSAGES_RECEIVED: messages_received,
                    ATTR_WEB_SOCKET_MESSAGES_IGNORED: messages_ignored,
                    ATTR_WEB_SOCKET_MESSAGES_HANDLED_PERCENTAGE: messages_handled_percentage
                }

                for key in system_state:
                    if key != IS_ALIVE:
                        attributes[key] = system_state[key]

                is_alive = system_state.get(IS_ALIVE, False)

            icon = CONNECTED_ICONS[is_alive]

            self.create_binary_sensor_entity(
                entity_name, is_alive, attributes, BinarySensorDeviceClass.CONNECTIVITY, icon
            )
        except Exception as ex:
            self.log_exception(ex, "Failed to create system status binary sensor")

    def create_device_tracker(self, host, data):
        try:
            allowed_items = self.config_data.device_trackers

            if host in allowed_items:
                entity_name = f"{self.integration_title} {host}"

                state = self.data_manager.is_device_online(host)

                attributes = {ATTR_SOURCE_TYPE: SOURCE_TYPE_ROUTER, CONF_HOST: host}

                entity = self.get_basic_entity(entity_name, DOMAIN_DEVICE_TRACKER, state, attributes)

                self.set_entity(DOMAIN_DEVICE_TRACKER, entity_name, entity)

        except Exception as ex:
            self.log_exception(
                ex,
                f"Failed to create {host} device tracker with the following data: {data}",
            )

    def create_binary_sensor_entity(
        self,
        name: str,
        state: int,
        attributes: dict,
        device_class: BinarySensorDeviceClass | None = None,
        icon: str | None = None,
    ):
        entity = self.get_basic_entity(name, DOMAIN_BINARY_SENSOR, state, attributes, icon)

        entity.binary_sensor_device_class = device_class

        self.set_entity(DOMAIN_BINARY_SENSOR, name, entity)

    def create_sensor_entity(
        self,
        name: str,
        state: StateType | date | datetime,
        attributes: dict,
        state_class: SensorStateClass | None = None,
        icon: str | None = None,
    ):
        entity = self.get_basic_entity(name, DOMAIN_BINARY_SENSOR, state, attributes, icon)

        entity.sensor_state_class = state_class

        self.set_entity(DOMAIN_SENSOR, name, entity)

    def _get_monitored_data(self, key):
        result = []

        if key == STATIC_DEVICES_KEY:
            result = self.config_data.monitored_devices

        elif key == INTERFACES_KEY:
            result = self.config_data.monitored_interfaces

        return result

    @staticmethod
    def _get_attributes(key, data):
        attributes = {}

        if key == STATIC_DEVICES_KEY:
            attributes = {
                "MAC": data.get("mac"),
                "Address": data.get("ip"),
            }
        elif key == INTERFACES_KEY:
            attributes = {
                LINK_ENABLED: data.get(LINK_ENABLED, FALSE_STR),
                "Link Speed (Mbps)": data.get("speed"),
                "Duplex": data.get("duplex"),
                "MAC": data.get("mac"),
                "Address": ", ".join(data.get("addresses", [])),
            }

        return attributes

    @staticmethod
    def get_basic_entity(
        name: str,
        domain: str,
        state: float,
        attributes: dict,
        icon: str | None = None,
    ):
        entity = EntityData()

        entity.name = name
        entity.state = state
        entity.attributes = attributes
        entity.device_name = DEFAULT_NAME
        entity.unique_id = f"{DEFAULT_NAME}-{domain}-{name}"

        if icon is not None:
            entity.icon = icon

        return entity

    @staticmethod
    def log_exception(ex, message):
        exc_type, exc_obj, tb = sys.exc_info()
        line_number = tb.tb_lineno

        _LOGGER.error(f"{message}, Error: {str(ex)}, Line: {line_number}")
