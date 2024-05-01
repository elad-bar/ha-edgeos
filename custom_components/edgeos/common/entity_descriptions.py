from copy import copy
from dataclasses import dataclass

from custom_components.edgeos.common.enums import (
    DeviceTypes,
    EntityKeys,
    UnitOfInterface,
)
from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntityDescription,
)
from homeassistant.components.number import NumberEntityDescription
from homeassistant.components.select import SelectEntityDescription
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.components.switch import SwitchEntityDescription
from homeassistant.const import (
    PERCENTAGE,
    Platform,
    UnitOfDataRate,
    UnitOfInformation,
    UnitOfTime,
)
from homeassistant.helpers.entity import EntityDescription


@dataclass(frozen=True, kw_only=True)
class IntegrationEntityDescription(EntityDescription):
    platform: Platform | None = None


@dataclass(frozen=True, kw_only=True)
class IntegrationBinarySensorEntityDescription(
    BinarySensorEntityDescription, IntegrationEntityDescription
):
    platform: Platform | None = Platform.BINARY_SENSOR
    on_value: str | bool | None = None
    attributes: list[str] | None = None


@dataclass(frozen=True, kw_only=True)
class IntegrationSensorEntityDescription(
    SensorEntityDescription, IntegrationEntityDescription
):
    platform: Platform | None = Platform.SENSOR


@dataclass(frozen=True, kw_only=True)
class IntegrationSelectEntityDescription(
    SelectEntityDescription, IntegrationEntityDescription
):
    platform: Platform | None = Platform.SELECT


@dataclass(frozen=True, kw_only=True)
class IntegrationSwitchEntityDescription(
    SwitchEntityDescription, IntegrationEntityDescription
):
    platform: Platform | None = Platform.SWITCH
    on_value: str | bool | None = None
    action_name: str | None = None


@dataclass(frozen=True, kw_only=True)
class IntegrationDeviceTrackerEntityDescription(IntegrationEntityDescription):
    platform: Platform | None = Platform.DEVICE_TRACKER


@dataclass(frozen=True, kw_only=True)
class IntegrationNumberEntityDescription(
    NumberEntityDescription, IntegrationEntityDescription
):
    platform: Platform | None = Platform.NUMBER


ENTITY_DESCRIPTIONS: list[IntegrationEntityDescription] = [
    IntegrationSensorEntityDescription(
        key=EntityKeys.CPU_USAGE,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    IntegrationSensorEntityDescription(
        key=EntityKeys.RAM_USAGE,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    IntegrationBinarySensorEntityDescription(
        key=EntityKeys.FIRMWARE, device_class=BinarySensorDeviceClass.UPDATE
    ),
    IntegrationSensorEntityDescription(
        key=EntityKeys.LAST_RESTART, device_class=SensorDeviceClass.TIMESTAMP
    ),
    IntegrationSensorEntityDescription(
        key=EntityKeys.UNKNOWN_DEVICES,
        native_unit_of_measurement="Devices",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    IntegrationSwitchEntityDescription(
        key=EntityKeys.LOG_INCOMING_MESSAGES,
    ),
    IntegrationNumberEntityDescription(
        key=EntityKeys.CONSIDER_AWAY_INTERVAL,
        native_max_value=600,
        native_min_value=0,
        native_unit_of_measurement=UnitOfTime.SECONDS,
    ),
    IntegrationNumberEntityDescription(
        key=EntityKeys.UPDATE_ENTITIES_INTERVAL,
        native_max_value=600,
        native_min_value=0,
        native_unit_of_measurement=UnitOfTime.SECONDS,
    ),
    IntegrationNumberEntityDescription(
        key=EntityKeys.UPDATE_API_INTERVAL,
        native_max_value=600,
        native_min_value=0,
        native_unit_of_measurement=UnitOfTime.SECONDS,
    ),
    IntegrationBinarySensorEntityDescription(
        key=EntityKeys.INTERFACE_CONNECTED,
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
    ),
    IntegrationSensorEntityDescription(
        key=EntityKeys.INTERFACE_RECEIVED_DROPPED,
        native_unit_of_measurement=UnitOfInterface.DROPPED,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    IntegrationSensorEntityDescription(
        key=EntityKeys.INTERFACE_SENT_DROPPED,
        native_unit_of_measurement=UnitOfInterface.DROPPED,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    IntegrationSensorEntityDescription(
        key=EntityKeys.INTERFACE_RECEIVED_ERRORS,
        native_unit_of_measurement=UnitOfInterface.ERRORS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    IntegrationSensorEntityDescription(
        key=EntityKeys.INTERFACE_SENT_ERRORS,
        native_unit_of_measurement=UnitOfInterface.ERRORS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    IntegrationSensorEntityDescription(
        key=EntityKeys.INTERFACE_RECEIVED_PACKETS,
        native_unit_of_measurement=UnitOfInterface.PACKETS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    IntegrationSensorEntityDescription(
        key=EntityKeys.INTERFACE_SENT_PACKETS,
        native_unit_of_measurement=UnitOfInterface.PACKETS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    IntegrationSensorEntityDescription(
        key=EntityKeys.INTERFACE_RECEIVED_RATE,
        native_unit_of_measurement=UnitOfDataRate.BYTES_PER_SECOND,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    IntegrationSensorEntityDescription(
        key=EntityKeys.INTERFACE_SENT_RATE,
        native_unit_of_measurement=UnitOfDataRate.BYTES_PER_SECOND,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    IntegrationSensorEntityDescription(
        key=EntityKeys.INTERFACE_RECEIVED_TRAFFIC,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    IntegrationSensorEntityDescription(
        key=EntityKeys.INTERFACE_SENT_TRAFFIC,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    IntegrationSwitchEntityDescription(
        key=EntityKeys.INTERFACE_MONITORED,
    ),
    IntegrationSwitchEntityDescription(
        key=EntityKeys.INTERFACE_STATUS,
    ),
    IntegrationSensorEntityDescription(
        key=EntityKeys.DEVICE_RECEIVED_RATE,
        native_unit_of_measurement=UnitOfDataRate.BYTES_PER_SECOND,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    IntegrationSensorEntityDescription(
        key=EntityKeys.DEVICE_SENT_RATE,
        native_unit_of_measurement=UnitOfDataRate.BYTES_PER_SECOND,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    IntegrationSensorEntityDescription(
        key=EntityKeys.DEVICE_RECEIVED_TRAFFIC,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    IntegrationSensorEntityDescription(
        key=EntityKeys.DEVICE_SENT_TRAFFIC,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    IntegrationDeviceTrackerEntityDescription(
        key=EntityKeys.DEVICE_TRACKER,
    ),
    IntegrationSwitchEntityDescription(
        key=EntityKeys.DEVICE_MONITORED,
    ),
]

ENTITY_DEVICE_MAPPING = {
    EntityKeys.CPU_USAGE: DeviceTypes.SYSTEM,
    EntityKeys.RAM_USAGE: DeviceTypes.SYSTEM,
    EntityKeys.FIRMWARE: DeviceTypes.SYSTEM,
    EntityKeys.LAST_RESTART: DeviceTypes.SYSTEM,
    EntityKeys.UNKNOWN_DEVICES: DeviceTypes.SYSTEM,
    EntityKeys.LOG_INCOMING_MESSAGES: DeviceTypes.SYSTEM,
    EntityKeys.CONSIDER_AWAY_INTERVAL: DeviceTypes.SYSTEM,
    EntityKeys.UPDATE_ENTITIES_INTERVAL: DeviceTypes.SYSTEM,
    EntityKeys.UPDATE_API_INTERVAL: DeviceTypes.SYSTEM,
    EntityKeys.INTERFACE_CONNECTED: DeviceTypes.INTERFACE,
    EntityKeys.INTERFACE_RECEIVED_DROPPED: DeviceTypes.INTERFACE,
    EntityKeys.INTERFACE_SENT_DROPPED: DeviceTypes.INTERFACE,
    EntityKeys.INTERFACE_RECEIVED_ERRORS: DeviceTypes.INTERFACE,
    EntityKeys.INTERFACE_SENT_ERRORS: DeviceTypes.INTERFACE,
    EntityKeys.INTERFACE_RECEIVED_PACKETS: DeviceTypes.INTERFACE,
    EntityKeys.INTERFACE_SENT_PACKETS: DeviceTypes.INTERFACE,
    EntityKeys.INTERFACE_RECEIVED_RATE: DeviceTypes.INTERFACE,
    EntityKeys.INTERFACE_SENT_RATE: DeviceTypes.INTERFACE,
    EntityKeys.INTERFACE_RECEIVED_TRAFFIC: DeviceTypes.INTERFACE,
    EntityKeys.INTERFACE_SENT_TRAFFIC: DeviceTypes.INTERFACE,
    EntityKeys.INTERFACE_MONITORED: DeviceTypes.INTERFACE,
    EntityKeys.INTERFACE_STATUS: DeviceTypes.INTERFACE,
    EntityKeys.DEVICE_RECEIVED_RATE: DeviceTypes.DEVICE,
    EntityKeys.DEVICE_SENT_RATE: DeviceTypes.DEVICE,
    EntityKeys.DEVICE_RECEIVED_TRAFFIC: DeviceTypes.DEVICE,
    EntityKeys.DEVICE_SENT_TRAFFIC: DeviceTypes.DEVICE,
    EntityKeys.DEVICE_TRACKER: DeviceTypes.DEVICE,
    EntityKeys.DEVICE_MONITORED: DeviceTypes.DEVICE,
}


def get_entity_descriptions(
    platform: Platform, device_type: DeviceTypes
) -> list[IntegrationEntityDescription]:
    entity_descriptions = copy(ENTITY_DESCRIPTIONS)

    result = [
        entity_description
        for entity_description in entity_descriptions
        if entity_description.platform == platform
        and ENTITY_DEVICE_MAPPING.get(entity_description.key) == device_type
    ]

    return result


def get_platforms() -> list[str]:
    platforms = {
        entity_description.platform: None for entity_description in ENTITY_DESCRIPTIONS
    }
    result = list(platforms.keys())

    return result


PLATFORMS = get_platforms()
