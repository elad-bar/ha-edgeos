from datetime import datetime
import logging
import sys

from homeassistant.helpers.device_registry import DeviceInfo

from ..common.consts import (
    API_DATA_DHCP_STATS,
    API_DATA_SYS_INFO,
    API_DATA_SYSTEM,
    DEFAULT_NAME,
    DHCP_SERVER_LEASED,
    DHCP_SERVER_STATS,
    DISCOVER_DATA_FW_VERSION,
    DISCOVER_DATA_PRODUCT,
    FW_LATEST_STATE_CAN_UPGRADE,
    SYSTEM_DATA_HOSTNAME,
    SYSTEM_DATA_LOGIN,
    SYSTEM_DATA_LOGIN_USER,
    SYSTEM_DATA_LOGIN_USER_LEVEL,
    SYSTEM_DATA_NTP,
    SYSTEM_DATA_NTP_SERVER,
    SYSTEM_DATA_OFFLOAD,
    SYSTEM_DATA_OFFLOAD_HW_NAT,
    SYSTEM_DATA_OFFLOAD_IPSEC,
    SYSTEM_DATA_TIME_ZONE,
    SYSTEM_DATA_TRAFFIC_ANALYSIS,
    SYSTEM_DATA_TRAFFIC_ANALYSIS_DPI,
    SYSTEM_DATA_TRAFFIC_ANALYSIS_EXPORT,
    SYSTEM_INFO_DATA_FW_LATEST,
    SYSTEM_INFO_DATA_FW_LATEST_STATE,
    SYSTEM_INFO_DATA_FW_LATEST_URL,
    SYSTEM_INFO_DATA_FW_LATEST_VERSION,
    SYSTEM_INFO_DATA_SW_VER,
    SYSTEM_STATS_DATA_CPU,
    SYSTEM_STATS_DATA_MEM,
    SYSTEM_STATS_DATA_UPTIME,
    WS_DISCOVER_KEY,
    WS_SYSTEM_STATS_KEY,
)
from ..common.enums import DeviceTypes
from ..models.config_data import ConfigData
from ..models.edge_os_system_data import EdgeOSSystemData
from .base_processor import BaseProcessor

_LOGGER = logging.getLogger(__name__)


class SystemProcessor(BaseProcessor):
    _system: EdgeOSSystemData | None = None

    def __init__(self, config_data: ConfigData):
        super().__init__(config_data)

        self.processor_type = DeviceTypes.SYSTEM

        self._system = None

    def get(self) -> EdgeOSSystemData:
        return self._system

    def get_device_info(self, item_id: str | None = None) -> DeviceInfo:
        device_info = DeviceInfo(
            identifiers={(DEFAULT_NAME, self._system.hostname)},
            name=self._system.hostname,
            model=self._system.product,
            manufacturer=DEFAULT_NAME,
            hw_version=self._system.fw_version,
        )

        return device_info

    def _process_api_data(self):
        super()._process_api_data()

        try:
            system_section = self._api_data.get(API_DATA_SYSTEM, {})
            system_info = self._api_data.get(API_DATA_SYS_INFO, {})
            system_details = system_section.get(API_DATA_SYSTEM, {})

            system_data = EdgeOSSystemData() if self._system is None else self._system

            system_data.hostname = system_section.get(SYSTEM_DATA_HOSTNAME)
            system_data.timezone = system_details.get(SYSTEM_DATA_TIME_ZONE)

            ntp: dict = system_details.get(SYSTEM_DATA_NTP, {})
            system_data.ntp_servers = ntp.get(SYSTEM_DATA_NTP_SERVER)

            offload: dict = system_details.get(SYSTEM_DATA_OFFLOAD, {})
            hardware_offload = EdgeOSSystemData.is_enabled(
                offload, SYSTEM_DATA_OFFLOAD_HW_NAT
            )
            ipsec_offload = EdgeOSSystemData.is_enabled(
                offload, SYSTEM_DATA_OFFLOAD_IPSEC
            )

            system_data.hardware_offload = hardware_offload
            system_data.ipsec_offload = ipsec_offload

            traffic_analysis: dict = system_details.get(
                SYSTEM_DATA_TRAFFIC_ANALYSIS, {}
            )
            dpi = EdgeOSSystemData.is_enabled(
                traffic_analysis, SYSTEM_DATA_TRAFFIC_ANALYSIS_DPI
            )
            traffic_analysis_export = EdgeOSSystemData.is_enabled(
                traffic_analysis, SYSTEM_DATA_TRAFFIC_ANALYSIS_EXPORT
            )

            system_data.deep_packet_inspection = dpi
            system_data.traffic_analysis_export = traffic_analysis_export

            sw_latest = system_info.get(SYSTEM_INFO_DATA_SW_VER)
            fw_latest = system_info.get(SYSTEM_INFO_DATA_FW_LATEST, {})

            fw_latest_state = fw_latest.get(SYSTEM_INFO_DATA_FW_LATEST_STATE)
            fw_latest_version = fw_latest.get(SYSTEM_INFO_DATA_FW_LATEST_VERSION)
            fw_latest_url = fw_latest.get(SYSTEM_INFO_DATA_FW_LATEST_URL)

            system_data.upgrade_available = (
                fw_latest_state == FW_LATEST_STATE_CAN_UPGRADE
            )
            system_data.upgrade_url = fw_latest_url
            system_data.upgrade_version = fw_latest_version

            system_data.sw_version = sw_latest

            login_details = system_details.get(SYSTEM_DATA_LOGIN, {})
            users = login_details.get(SYSTEM_DATA_LOGIN_USER, {})
            current_user = users.get(self._config_data.username, {})
            system_data.user_level = current_user.get(SYSTEM_DATA_LOGIN_USER_LEVEL)

            self._system = system_data

            message = (
                f"User {self._config_data.username} level is {self._system.user_level}, "
                f"Interface status switch will not be created as it requires admin role"
            )

            self._unique_log(logging.INFO, message)

            self._update_leased_devices()

            warning_messages = []

            if not self._system.deep_packet_inspection:
                warning_messages.append("DPI (deep packet inspection) is turned off")

            if not self._system.traffic_analysis_export:
                warning_messages.append("Traffic Analysis Export is turned off")

            if len(warning_messages) > 0:
                warning_message = " and ".join(warning_messages)

                self._unique_log(
                    logging.WARNING,
                    f"Integration will not work correctly since {warning_message}",
                )

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(
                f"Failed to extract System data, Error: {ex}, Line: {line_number}"
            )

    def _process_ws_data(self):
        try:
            system_stats_data = self._ws_data.get(WS_SYSTEM_STATS_KEY, {})
            discovery_data = self._ws_data.get(WS_DISCOVER_KEY, {})

            system_data = self._system

            system_data.fw_version = discovery_data.get(DISCOVER_DATA_FW_VERSION)
            system_data.product = discovery_data.get(DISCOVER_DATA_PRODUCT)

            uptime = float(system_stats_data.get(SYSTEM_STATS_DATA_UPTIME, 0))

            system_data.cpu = int(system_stats_data.get(SYSTEM_STATS_DATA_CPU, 0))
            system_data.mem = int(system_stats_data.get(SYSTEM_STATS_DATA_MEM, 0))

            if uptime != system_data.uptime:
                system_data.uptime = uptime
                system_data.last_reset = self._get_last_reset(uptime)

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(
                f"Failed to update system statistics, "
                f"Error: {ex}, "
                f"Line: {line_number}"
            )

    def _update_leased_devices(self):
        try:
            unknown_devices = 0
            data_leases_stats = self._api_data.get(API_DATA_DHCP_STATS, {})

            subnets = data_leases_stats.get(DHCP_SERVER_STATS, {})

            for subnet in subnets:
                subnet_data = subnets.get(subnet, {})
                unknown_devices += int(subnet_data.get(DHCP_SERVER_LEASED, 0))

            self._system.leased_devices = unknown_devices

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(
                f"Failed to extract Unknown Devices data, Error: {ex}, Line: {line_number}"
            )

    @staticmethod
    def _get_last_reset(uptime):
        now = datetime.now().timestamp()
        last_reset = now - uptime

        result = datetime.fromtimestamp(last_reset)

        return result
