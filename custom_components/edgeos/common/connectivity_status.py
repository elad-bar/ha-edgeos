import logging

from homeassistant.const import StrEnum


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
        if status in [
            ConnectivityStatus.Connected,
            ConnectivityStatus.Connecting,
            ConnectivityStatus.Disconnected,
            ConnectivityStatus.TemporaryConnected,
        ]:
            return logging.INFO
        elif status in [ConnectivityStatus.NotConnected]:
            return logging.WARNING
        else:
            return logging.ERROR

    @staticmethod
    def get_ha_error(status: str) -> str | None:
        errors = {
            str(ConnectivityStatus.InvalidCredentials): "invalid_admin_credentials",
            str(ConnectivityStatus.TemporaryConnected): "missing_permanent_api_key",
            str(ConnectivityStatus.MissingAPIKey): "missing_permanent_api_key",
            str(ConnectivityStatus.Failed): "invalid_server_details",
            str(ConnectivityStatus.NotFound): "invalid_server_details",
        }

        error_id = errors.get(status)

        return error_id
