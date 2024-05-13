import logging
import sys

from homeassistant.helpers.device_registry import DeviceInfo

from ..common.consts import (
    ADDRESS_LIST,
    API_DATA_INTERFACES,
    API_DATA_SYSTEM,
    DEFAULT_NAME,
    FALSE_STR,
    INTERFACE_DATA_ADDRESS,
    INTERFACE_DATA_AGING,
    INTERFACE_DATA_BRIDGE_GROUP,
    INTERFACE_DATA_BRIDGED_CONNTRACK,
    INTERFACE_DATA_DESCRIPTION,
    INTERFACE_DATA_DUPLEX,
    INTERFACE_DATA_HELLO_TIME,
    INTERFACE_DATA_LINK_UP,
    INTERFACE_DATA_MAC,
    INTERFACE_DATA_MAX_AGE,
    INTERFACE_DATA_MULTICAST,
    INTERFACE_DATA_PRIORITY,
    INTERFACE_DATA_PROMISCUOUS,
    INTERFACE_DATA_SPEED,
    INTERFACE_DATA_STP,
    INTERFACE_DATA_UP,
    TRAFFIC_DATA_INTERFACE_ITEMS,
    TRUE_STR,
    WS_INTERFACES_KEY,
)
from ..common.enums import DeviceTypes, InterfaceTypes
from ..models.config_data import ConfigData
from ..models.edge_os_interface_data import EdgeOSInterfaceData
from .base_processor import BaseProcessor

_LOGGER = logging.getLogger(__name__)


class InterfaceProcessor(BaseProcessor):
    _interfaces: dict[str, EdgeOSInterfaceData]

    def __init__(self, config_data: ConfigData):
        super().__init__(config_data)

        self.processor_type = DeviceTypes.INTERFACE

        self._interfaces: dict[str, EdgeOSInterfaceData] = {}

    def get_interfaces(self) -> list[str]:
        return list(self._interfaces.keys())

    def get_all(self) -> list[dict]:
        items = [self._interfaces[item_key].to_dict() for item_key in self._interfaces]

        return items

    def get_interface(self, identifiers: set[tuple[str, str]]) -> dict | None:
        interface: dict | None = None
        interface_identifier = list(identifiers)[0][1]

        for interface_name in self._interfaces:
            unique_id = self._get_device_info_unique_id(interface_name)

            if unique_id == interface_identifier:
                interface = self._interfaces[interface_name].to_dict()

        return interface

    def get_data(self, interface_name: str) -> EdgeOSInterfaceData:
        interface_data = self._interfaces.get(interface_name)

        return interface_data

    def get_device_info(self, item_id: str | None = None) -> DeviceInfo:
        interface_name = item_id.upper()

        device_name = self._get_device_info_name(interface_name)

        unique_id = self._get_device_info_unique_id(interface_name)

        device_info = DeviceInfo(
            identifiers={(DEFAULT_NAME, unique_id)},
            name=device_name,
            model=self.processor_type,
            manufacturer=DEFAULT_NAME,
            via_device=(DEFAULT_NAME, self._hostname),
        )

        return device_info

    def _process_api_data(self):
        super()._process_api_data()

        try:
            system_section = self._api_data.get(API_DATA_SYSTEM, {})
            interface_types = system_section.get(API_DATA_INTERFACES, {})

            for interface_type in interface_types:
                interfaces = interface_types.get(interface_type)

                if interfaces is not None:
                    for interface_name in interfaces:
                        interface_data = interfaces.get(interface_name, {})
                        int_type = InterfaceTypes(interface_type)

                        self._extract_interface(
                            interface_name, interface_data, int_type
                        )

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(
                f"Failed to extract Interfaces data, Error: {ex}, Line: {line_number}"
            )

    def _process_ws_data(self):
        try:
            interfaces_data = self._ws_data.get(WS_INTERFACES_KEY, {})

            for name in interfaces_data:
                interface_item = self._interfaces.get(name)
                stats = interfaces_data.get(name)

                if interface_item is None:
                    interface_data = interfaces_data.get(name)
                    interface_item = self._extract_interface(
                        name, interface_data, InterfaceTypes.DYNAMIC
                    )

                if interface_item is not None:
                    self._update_interface_stats(interface_item, stats)

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(
                f"Failed to extract WS data, Error: {ex}, Line: {line_number}"
            )

    def _extract_interface(
        self, name: str, data: dict, interface_type: InterfaceTypes
    ) -> EdgeOSInterfaceData:
        interface = self._interfaces.get(name)

        try:
            if data is not None:
                if interface is None:
                    interface = EdgeOSInterfaceData(name, interface_type)
                else:
                    interface.update_interface_type(interface_type)

                interface.description = data.get(INTERFACE_DATA_DESCRIPTION)
                interface.duplex = data.get(INTERFACE_DATA_DUPLEX)
                interface.speed = data.get(INTERFACE_DATA_SPEED)
                interface.bridge_group = data.get(INTERFACE_DATA_BRIDGE_GROUP)
                interface.address = data.get(INTERFACE_DATA_ADDRESS)
                interface.aging = data.get(INTERFACE_DATA_AGING)
                interface.bridged_conntrack = data.get(INTERFACE_DATA_BRIDGED_CONNTRACK)
                interface.hello_time = data.get(INTERFACE_DATA_HELLO_TIME)
                interface.max_age = data.get(INTERFACE_DATA_MAX_AGE)
                interface.priority = data.get(INTERFACE_DATA_PRIORITY)
                interface.promiscuous = data.get(INTERFACE_DATA_PROMISCUOUS)
                interface.stp = (
                    data.get(INTERFACE_DATA_STP, FALSE_STR).lower() == TRUE_STR
                )

                self._interfaces[interface.unique_id] = interface

                if not interface.is_supported:
                    self._unique_log(
                        logging.INFO,
                        f"Ignoring interface {interface.name}, Interface type: {interface_type}",
                    )

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(
                f"Failed to extract interface data for {name}/{interface_type}, "
                f"Error: {ex}, "
                f"Line: {line_number}"
            )

        return interface

    @staticmethod
    def _update_interface_stats(interface: EdgeOSInterfaceData, stats: dict):
        try:
            if stats is not None:
                interface.up = (
                    str(stats.get(INTERFACE_DATA_UP, False)).lower() == TRUE_STR
                )
                interface.l1up = (
                    str(stats.get(INTERFACE_DATA_LINK_UP, False)).lower() == TRUE_STR
                )
                interface.mac = stats.get(INTERFACE_DATA_MAC)
                interface.multicast = stats.get(INTERFACE_DATA_MULTICAST, 0)
                interface.address = stats.get(ADDRESS_LIST, [])

                directions = [interface.received, interface.sent]

                for direction in directions:
                    stat_data = {}
                    for stat_key in TRAFFIC_DATA_INTERFACE_ITEMS:
                        key = f"{direction.direction}_{stat_key}"
                        stat_data_item = TRAFFIC_DATA_INTERFACE_ITEMS.get(stat_key)

                        stat_data[stat_data_item] = float(stats.get(key))

                    direction.update(stat_data)

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(
                f"Failed to update interface statistics for {interface.name}, "
                f"Error: {ex}, "
                f"Line: {line_number}"
            )
