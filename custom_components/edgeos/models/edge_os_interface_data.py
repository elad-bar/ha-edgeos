from __future__ import annotations

from ..common.consts import (
    INTERFACE_DATA_ADDRESS,
    INTERFACE_DATA_AGING,
    INTERFACE_DATA_BRIDGE_GROUP,
    INTERFACE_DATA_BRIDGED_CONNTRACK,
    INTERFACE_DATA_DESCRIPTION,
    INTERFACE_DATA_DUPLEX,
    INTERFACE_DATA_HELLO_TIME,
    INTERFACE_DATA_IS_SUPPORTED,
    INTERFACE_DATA_MAX_AGE,
    INTERFACE_DATA_MULTICAST,
    INTERFACE_DATA_NAME,
    INTERFACE_DATA_PRIORITY,
    INTERFACE_DATA_PROMISCUOUS,
    INTERFACE_DATA_RECEIVED,
    INTERFACE_DATA_SENT,
    INTERFACE_DATA_SPEED,
    INTERFACE_DATA_STP,
    INTERFACE_DATA_TYPE,
    INTERFACE_DYNAMIC_SUPPORTED,
    RECEIVED_DROPPED_PREFIX,
    RECEIVED_ERRORS_PREFIX,
    RECEIVED_PACKETS_PREFIX,
    RECEIVED_RATE_PREFIX,
    RECEIVED_TRAFFIC_PREFIX,
    SENT_DROPPED_PREFIX,
    SENT_ERRORS_PREFIX,
    SENT_PACKETS_PREFIX,
    SENT_RATE_PREFIX,
    SENT_TRAFFIC_PREFIX,
    TRAFFIC_DATA_DIRECTION_RECEIVED,
    TRAFFIC_DATA_DIRECTION_SENT,
)
from ..common.enums import DynamicInterfaceTypes, InterfaceTypes
from .edge_os_traffic_data import EdgeOSTrafficData


class EdgeOSInterfaceData:
    name: str
    interface_type: InterfaceTypes | None
    duplex: str | None
    speed: str | None
    description: str | None
    bridge_group: str | None
    address: list | None
    aging: str | None
    bridged_conntrack: str | None
    hello_time: str | None
    max_age: str | None
    priority: str | None
    promiscuous: str | None
    stp: bool | None
    multicast: float | None
    received: EdgeOSTrafficData
    sent: EdgeOSTrafficData
    up: bool | None
    l1up: bool | None
    mac: str | None
    is_supported: bool

    def __init__(self, name: str, interface_type: InterfaceTypes):
        self.name = name
        self.interface_type = interface_type
        self.description = None
        self.duplex = None
        self.speed = None
        self.bridge_group = None
        self.address = None
        self.aging = None
        self.bridged_conntrack = None
        self.hello_time = None
        self.max_age = None
        self.priority = None
        self.promiscuous = None
        self.stp = None
        self.multicast = None
        self.received = EdgeOSTrafficData(TRAFFIC_DATA_DIRECTION_RECEIVED)
        self.sent = EdgeOSTrafficData(TRAFFIC_DATA_DIRECTION_SENT)

        self.up = None
        self.l1up = None
        self.mac = None
        self.is_supported = self._get_is_supported()

    @property
    def unique_id(self) -> str:
        return self.name

    def to_dict(self):
        obj = {
            INTERFACE_DATA_NAME: self.name,
            INTERFACE_DATA_DESCRIPTION: self.description,
            INTERFACE_DATA_TYPE: self.interface_type,
            INTERFACE_DATA_IS_SUPPORTED: self.is_supported,
            INTERFACE_DATA_DUPLEX: self.duplex,
            INTERFACE_DATA_SPEED: self.speed,
            INTERFACE_DATA_BRIDGE_GROUP: self.bridge_group,
            INTERFACE_DATA_ADDRESS: self.address,
            INTERFACE_DATA_AGING: self.aging,
            INTERFACE_DATA_BRIDGED_CONNTRACK: self.bridged_conntrack,
            INTERFACE_DATA_HELLO_TIME: self.hello_time,
            INTERFACE_DATA_MAX_AGE: self.max_age,
            INTERFACE_DATA_PRIORITY: self.priority,
            INTERFACE_DATA_PROMISCUOUS: self.promiscuous,
            INTERFACE_DATA_STP: self.stp,
            INTERFACE_DATA_MULTICAST: self.multicast,
            INTERFACE_DATA_RECEIVED: self.received.to_dict(),
            INTERFACE_DATA_SENT: self.sent.to_dict(),
        }

        return obj

    def _get_is_supported(self):
        is_supported = self.interface_type in [
            InterfaceTypes.ETHERNET,
            InterfaceTypes.BRIDGE,
        ]

        if self.interface_type == InterfaceTypes.DYNAMIC:
            prefixes = list(DynamicInterfaceTypes)

            for prefix in prefixes:
                if self.name.startswith(str(prefix)):
                    is_supported = prefix in INTERFACE_DYNAMIC_SUPPORTED
                    break

        return is_supported

    def get_stats(self):
        data = {
            RECEIVED_RATE_PREFIX: self.received.rate,
            RECEIVED_TRAFFIC_PREFIX: self.received.total,
            RECEIVED_DROPPED_PREFIX: self.received.dropped,
            RECEIVED_ERRORS_PREFIX: self.received.errors,
            RECEIVED_PACKETS_PREFIX: self.received.packets,
            SENT_RATE_PREFIX: self.sent.rate,
            SENT_TRAFFIC_PREFIX: self.sent.total,
            SENT_DROPPED_PREFIX: self.sent.dropped,
            SENT_ERRORS_PREFIX: self.sent.errors,
            SENT_PACKETS_PREFIX: self.sent.packets,
        }

        return data

    def get_attributes(self):
        interface_attributes = self.to_dict()

        attributes = {
            attribute: interface_attributes[attribute]
            for attribute in interface_attributes
            if attribute
            not in [
                INTERFACE_DATA_RECEIVED,
                INTERFACE_DATA_SENT,
                INTERFACE_DATA_IS_SUPPORTED,
            ]
            and interface_attributes[attribute] is not None
        }

        return attributes

    def __repr__(self):
        to_string = f"{self.to_dict()}"

        return to_string
