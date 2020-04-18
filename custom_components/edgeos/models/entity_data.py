from ..helpers.const import *


class EntityData:
    unique_id: str
    name: str
    state: int
    attributes: dict
    icon: str
    device_name: str
    status: str

    def __init__(self):
        self.unique_id = ""
        self.name = ""
        self.state = 0
        self.attributes = {}
        self.icon = ""
        self.device_name = ""
        self.status = ENTITY_STATUS_CREATED

    def __repr__(self):
        obj = {
            ENTITY_NAME: self.name,
            ENTITY_STATE: self.state,
            ENTITY_ATTRIBUTES: self.attributes,
            ENTITY_ICON: self.icon,
            ENTITY_DEVICE_NAME: self.device_name,
            ENTITY_STATUS: self.status,
            ENTITY_UNIQUE_ID: self.status
        }

        to_string = f"{obj}"

        return to_string
