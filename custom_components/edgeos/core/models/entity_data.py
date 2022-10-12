from __future__ import annotations

from datetime import datetime

from homeassistant.helpers.entity import EntityDescription
from homeassistant.util import slugify

from ..helpers.const import *
from ..helpers.enums import EntityStatus


class EntityData:
    state: str | int | float | bool | datetime | None
    attributes: dict
    details: dict
    device_name: str | None
    status: EntityStatus
    disabled: bool
    domain: str | None
    entry_id: str
    entity_description: EntityDescription

    def __init__(self, entry_id: str, entity_description: EntityDescription):
        self.entry_id = entry_id
        self.entity_description = entity_description
        self.state = None
        self.attributes = {}
        self.details = {}
        self.device_name = None
        self.status = EntityStatus.CREATED
        self.disabled = False
        self.domain = None

    @property
    def id(self):
        return self.entity_description.key

    @property
    def name(self):
        return self.entity_description.name

    def __repr__(self):
        obj = {
            ENTITY_UNIQUE_ID: self.id,
            ENTITY_STATE: self.state,
            ENTITY_ATTRIBUTES: self.attributes,
            ENTITY_DETAILS: self.details,
            ENTITY_DEVICE_NAME: self.device_name,
            ENTITY_STATUS: self.status,
            ENTITY_DISABLED: self.disabled,
            ENTITY_DOMAIN: self.domain,
            ENTITY_CONFIG_ENTRY_ID: self.entry_id
        }

        to_string = f"{obj}"

        return to_string

    @staticmethod
    def generate_unique_id(domain, name):
        unique_id = slugify(f"{domain} {name}")

        return unique_id
