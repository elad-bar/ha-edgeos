from __future__ import annotations

from ..helpers.const import *
from .edge_os_traffic_data import EdgeOSTrafficData


class EdgeOSInterfaceData:
    name: str
    interface_type: str
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

    def __init__(self, name: str, interface_type: str):
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

    @property
    def unique_id(self) -> str:
        return self.name

    def update_stats(self, data: dict):
        data_stats = data.get(INTERFACE_DATA_STATS, {})

        self.up = str(data.get(INTERFACE_DATA_UP, False)).lower() == str(True).lower()
        self.l1up = str(data.get(INTERFACE_DATA_L1UP, False)).lower() == str(True).lower()
        self.mac = data.get(INTERFACE_DATA_MAC)
        self.multicast = float(data_stats.get(INTERFACE_DATA_MULTICAST, "0"))

        directions = [self.received, self.sent]

        for direction in directions:
            stat_data = {}
            for stat_key in TRAFFIC_DATA_INTERFACE_ITEMS:
                key = f"{direction.direction}_{stat_key}"
                stat_data_item = TRAFFIC_DATA_INTERFACE_ITEMS.get(key)

                stat_data[stat_data_item] = float(data_stats.get(key))

            direction.update(stat_data)

    def to_dict(self):
        obj = {
            INTERFACE_DATA_NAME: self.name,
            INTERFACE_DATA_DESCRIPTION: self.description,
            INTERFACE_DATA_INTERFACE_TYPE: self.interface_type,
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
            ENTITY_UNIQUE_ID: self.unique_id
        }

        return obj

    def __repr__(self):
        to_string = f"{self.to_dict()}"

        return to_string
