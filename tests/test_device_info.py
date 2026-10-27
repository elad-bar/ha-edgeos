from types import SimpleNamespace

from custom_components.edgeos.common.consts import DEFAULT_NAME
from custom_components.edgeos.common.enums import DeviceTypes
from custom_components.edgeos.data_processors.base_processor import BaseProcessor
from custom_components.edgeos.data_processors.device_processor import DeviceProcessor
from custom_components.edgeos.data_processors.interface_processor import (
    InterfaceProcessor,
)
from custom_components.edgeos.managers.coordinator import Coordinator
from custom_components.edgeos.models.config_data import ConfigData
from custom_components.edgeos.models.edge_os_device_data import EdgeOSDeviceData

ROUTER_HOSTNAME = "router"
PARENT_DEVICE_ID = "registered-parent-device-id"


def test_base_processor_device_info_uses_parent_device_id():
    processor = BaseProcessor(ConfigData())
    processor._hostname = ROUTER_HOSTNAME
    processor.processor_type = DeviceTypes.SYSTEM

    device_info = processor.get_device_info(via_device_id=PARENT_DEVICE_ID)

    assert device_info["via_device_id"] == PARENT_DEVICE_ID
    assert "via_device" not in device_info


def test_device_processor_device_info_uses_parent_device_id():
    processor = DeviceProcessor(ConfigData())
    processor._hostname = ROUTER_HOSTNAME
    processor._devices["00:11:22:33:44:55"] = EdgeOSDeviceData(
        "client", "192.0.2.2", "00:11:22:33:44:55", None, False
    )

    device_info = processor.get_device_info(
        "00:11:22:33:44:55", via_device_id=PARENT_DEVICE_ID
    )

    assert device_info["via_device_id"] == PARENT_DEVICE_ID
    assert "via_device" not in device_info


def test_interface_processor_device_info_uses_parent_device_id():
    processor = InterfaceProcessor(ConfigData())
    processor._hostname = ROUTER_HOSTNAME

    device_info = processor.get_device_info("eth0", via_device_id=PARENT_DEVICE_ID)

    assert device_info["via_device_id"] == PARENT_DEVICE_ID
    assert "via_device" not in device_info


def test_coordinator_uses_registered_parent_device_id(monkeypatch):
    parent_identifiers = {(DEFAULT_NAME, ROUTER_HOSTNAME)}
    parent_device_info = {
        "identifiers": parent_identifiers,
        "name": ROUTER_HOSTNAME,
        "manufacturer": DEFAULT_NAME,
    }

    class DeviceRegistry:
        def async_get_device(self, identifiers):
            assert identifiers == parent_identifiers
            return None

        def async_get_or_create(self, **kwargs):
            assert kwargs["config_entry_id"] == "entry-id"
            assert kwargs["identifiers"] == parent_identifiers
            return SimpleNamespace(id=PARENT_DEVICE_ID)

    monkeypatch.setattr(
        "custom_components.edgeos.managers.coordinator.dr.async_get",
        lambda hass: DeviceRegistry(),
    )
    coordinator = SimpleNamespace(
        hass=object(),
        _config_manager=SimpleNamespace(entry_id="entry-id"),
        _system_processor=SimpleNamespace(
            get_device_info=lambda: parent_device_info
        ),
    )

    parent_device_id = Coordinator._get_parent_device_id(coordinator)

    assert parent_device_id == PARENT_DEVICE_ID
