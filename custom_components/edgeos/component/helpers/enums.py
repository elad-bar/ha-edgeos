from enum import Enum

from homeassistant.backports.enum import StrEnum


class InterfaceTypes(StrEnum):
    BRIDGE = "bridge"
    LOOPBACK = "loopback"
    ETHERNET = "ethernet"

    PPPOE_PREFIX = "pppoe"
    SWITCH_PREFIX = "switch"
    VIRTUAL_TUNNEL_PREFIX = "vtun"
    OPEN_VPN_PREFIX = "openvpn"
    BONDING_PREFIX = "bond"
    INTERMEDIATE_QUEUEING_DEVICE_PREFIX = "imq"
    NETWORK_PROGRAMMING_INTERFACE_PREFIX = "npi"
    LOOPBACK_PREFIX = "lo"


class InterfaceHandlers(Enum):
    REGULAR = 0
    SPECIAL = 1
    IGNORED = 99
