from enum import StrEnum


class DeviceTypes(StrEnum):
    SYSTEM = "System"
    DEVICE = "Device"
    INTERFACE = "Interface"


class InterfaceTypes(StrEnum):
    BRIDGE = "bridge"
    LOOPBACK = "loopback"
    ETHERNET = "ethernet"
    SWITCH = "switch"
    OPEN_VPN = "openvpn"
    WIREGUARD = "wireguard"
    DYNAMIC = "dynamic"


class DynamicInterfaceTypes(StrEnum):
    PPPOE = "pppoe"
    VIRTUAL_TUNNEL = "vtun"
    BONDING = "bond"
    INTERMEDIATE_QUEUEING_DEVICE = "imq"
    NETWORK_PROGRAMMING_INTERFACE = "npi"
    LOOPBACK = "lo"


class EntityKeys(StrEnum):
    CPU_USAGE = "cpu_usage"
    RAM_USAGE = "ram_usage"
    FIRMWARE = "firmware"
    LAST_RESTART = "last_restart"
    UNKNOWN_DEVICES = "unknown_devices"
    LOG_INCOMING_MESSAGES = "log_incoming_messages"
    CONSIDER_AWAY_INTERVAL = "consider_away_interval"
    UPDATE_ENTITIES_INTERVAL = "update_entities_interval"
    UPDATE_API_INTERVAL = "update_api_interval"
    UNIT = "unit"

    INTERFACE_CONNECTED = "interface_connected"
    INTERFACE_RECEIVED_DROPPED = "interface_received_dropped"
    INTERFACE_SENT_DROPPED = "interface_sent_dropped"
    INTERFACE_RECEIVED_ERRORS = "interface_received_errors"
    INTERFACE_SENT_ERRORS = "interface_sent_errors"
    INTERFACE_RECEIVED_PACKETS = "interface_received_packets"
    INTERFACE_SENT_PACKETS = "interface_sent_packets"
    INTERFACE_RECEIVED_RATE = "interface_received_rate"
    INTERFACE_SENT_RATE = "interface_sent_rate"
    INTERFACE_RECEIVED_TRAFFIC = "interface_received_traffic"
    INTERFACE_SENT_TRAFFIC = "interface_sent_traffic"
    INTERFACE_MONITORED = "interface_monitored"
    INTERFACE_STATUS = "interface_status"

    DEVICE_RECEIVED_RATE = "device_received_rate"
    DEVICE_SENT_RATE = "device_sent_rate"
    DEVICE_RECEIVED_TRAFFIC = "device_received_traffic"
    DEVICE_SENT_TRAFFIC = "device_sent_traffic"
    DEVICE_TRACKER = "device_tracker"
    DEVICE_MONITORED = "device_monitored"


class UnitOfEdgeOS(StrEnum):
    ERRORS = "Errors"
    DROPPED = "Dropped"
    PACKETS = "Packets"
    DEVICES = "Devices"


class EntityValidation(StrEnum):
    MONITORED = "monitored"
    ADMIN_ONLY = "admin-only"
    NON_ADMIN_ONLY = "non-admin-only"
