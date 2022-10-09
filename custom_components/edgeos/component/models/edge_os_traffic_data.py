from __future__ import annotations

from ..helpers.const import *


class EdgeOSTrafficData:
    direction: str
    rate: float
    total: float
    dropped: float | None
    errors: float | None
    packets: float | None
    last_activity: float

    def __init__(self, direction: str):
        self.direction = direction
        self.rate = 0
        self.total = 0
        self.dropped = None
        self.errors = None
        self.packets = None
        self.last_activity = 0

    def update(self, data: dict):
        self.rate = data.get(TRAFFIC_DATA_RATE, 0)
        self.total = data.get(TRAFFIC_DATA_TOTAL, 0)
        self.dropped = data.get(TRAFFIC_DATA_DROPPED)
        self.errors = data.get(TRAFFIC_DATA_ERRORS)
        self.packets = data.get(TRAFFIC_DATA_PACKETS)

        if self.rate > 0:
            now = datetime.now().timestamp()
            self.last_activity = now

    def to_dict(self):
        now = datetime.now().timestamp()
        diff = "N/A" if self.last_activity == 0 else timedelta(seconds=(now - self.last_activity)).total_seconds()

        obj = {
            TRAFFIC_DATA_DIRECTION: self.direction,
            TRAFFIC_DATA_RATE: self.rate,
            TRAFFIC_DATA_TOTAL: self.total,
            TRAFFIC_DATA_LAST_ACTIVITY: self.last_activity,
            TRAFFIC_DATA_LAST_ACTIVITY_IN_SECONDS: diff
        }

        if self.errors is not None:
            obj[TRAFFIC_DATA_ERRORS] = self.errors

        if self.packets is not None:
            obj[TRAFFIC_DATA_PACKETS] = self.packets

        if self.dropped is not None:
            obj[TRAFFIC_DATA_DROPPED] = self.dropped

        return obj

    def __repr__(self):
        to_string = f"{self.to_dict()}"

        return to_string
