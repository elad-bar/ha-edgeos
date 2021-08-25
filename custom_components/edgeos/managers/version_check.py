import logging
from typing import Optional

from ..helpers.const import *
from ..models.exceptions import IncompatibleVersion

_LOGGER = logging.getLogger(__name__)


class VersionManager:
    version: Optional[str]

    def __init__(self):
        self.version = None

    def validate(self):
        if self.version is None:
            raise IncompatibleVersion(self.version)

        if self.version == EDGEOS_VERSION_UNKNOWN:
            raise IncompatibleVersion(self.version)

        if self.version[:2] == EDGEOS_VERSION_INCOMPATIBLE:
            raise IncompatibleVersion(self.version)

    def update(self, system_info_data):
        firmware_version = system_info_data.get("fw-latest", None)
        if firmware_version is None:
            software_version = system_info_data.get("sw_ver", "N/A")
            software_version_items = software_version.split(".")

            version_without_build = software_version_items[:-3]
            version_without_model = version_without_build[2:]
            version = '.'.join(version_without_model)

        else:
            version = firmware_version.get("version", "N/A")

        self.version = version
