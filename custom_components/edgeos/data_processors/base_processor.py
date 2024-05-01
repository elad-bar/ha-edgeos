import logging

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.util import slugify

from ..common.consts import API_DATA_SYSTEM, DEFAULT_NAME, SYSTEM_DATA_HOSTNAME
from ..common.enums import DeviceTypes
from ..models.config_data import ConfigData

_LOGGER = logging.getLogger(__name__)


class BaseProcessor:
    _api_data: dict | None = None
    _ws_data: dict | None = None
    _config_data: ConfigData | None = None
    _unique_messages: list[str] | None = None
    processor_type: DeviceTypes | None = None
    _hostname: str | None = None

    def __init__(self, config_data: ConfigData):
        self._config_data = config_data

        self._api_data = None
        self._ws_data = None
        self.processor_type = None
        self._hostname = None

        self._unique_messages = []

    def update(self, api_data: dict, ws_data: dict):
        self._api_data = api_data
        self._ws_data = ws_data

        self._process_api_data()
        self._process_ws_data()

    def _process_api_data(self):
        system_details = self._api_data.get(API_DATA_SYSTEM, {})

        self._hostname = system_details.get(SYSTEM_DATA_HOSTNAME)

    def _process_ws_data(self):
        pass

    def _unique_log(self, log_level: int, message: str):
        if message not in self._unique_messages:
            self._unique_messages.append(message)

            _LOGGER.log(log_level, self._unique_messages)

    def get_device_info(self, item_id: str | None = None) -> DeviceInfo:
        device_name = self._get_device_info_name(item_id)

        unique_id = self._get_device_info_unique_id(item_id)

        device_info = DeviceInfo(
            identifiers={(DEFAULT_NAME, unique_id)},
            name=device_name,
            model=self.processor_type,
            manufacturer=DEFAULT_NAME,
            # via_device=(DEFAULT_NAME, self._hostname)
        )

        return device_info

    def _get_device_info_name(self, item_id: str | None = None):
        parts = [self._hostname, self.processor_type, item_id]

        relevant_parts = [part for part in parts if part is not None]

        name = " ".join(relevant_parts)

        return name

    def _get_device_info_unique_id(self, item_id: str | None = None):
        identifier = self._get_device_info_name(item_id)

        unique_id = slugify(identifier)

        return unique_id
