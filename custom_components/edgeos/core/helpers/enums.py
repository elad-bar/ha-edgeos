import logging

from homeassistant.backports.enum import StrEnum


class ConnectivityStatus(StrEnum):
    NotConnected = "Not connected"
    Connecting = "Establishing connection to API"
    Connected = "Connected to the API"
    TemporaryConnected = "Connected with temporary API key"
    Failed = "Failed to access API"
    InvalidCredentials = "Invalid credentials"
    MissingAPIKey = "Permanent API Key was not found"
    Disconnected = "Disconnected by the system"
    NotFound = "API Not found"

    @staticmethod
    def get_log_level(status: StrEnum) -> int:
        if status == ConnectivityStatus.Connected:
            return logging.DEBUG
        elif status in [ConnectivityStatus.Disconnected]:
            return logging.INFO
        elif status in [ConnectivityStatus.NotConnected, ConnectivityStatus.Connecting]:
            return logging.WARNING
        else:
            return logging.ERROR


class EntityStatus(StrEnum):
    EMPTY = "empty"
    READY = "ready"
    CREATED = "created"
    DELETED = "deleted"
    UPDATED = "updated"
