from homeassistant.exceptions import HomeAssistantError

from ...core.helpers.enums import ConnectivityStatus


class MonitorNotFoundError(HomeAssistantError):
    monitor_id: str

    def __init__(self, monitor_id: str):
        self.monitor_id = monitor_id


class APIValidationException(Exception):
    endpoint: str
    status: ConnectivityStatus

    def __init__(self, endpoint: str, status: ConnectivityStatus):
        super().__init__(
            f"API cannot process request to '{endpoint}', Status: {status}"
        )

        self.endpoint = endpoint
        self.status = status


class AlreadyExistsError(HomeAssistantError):
    title: str

    def __init__(self, title: str):
        self.title = title


class LoginError(HomeAssistantError):
    errors: dict

    def __init__(self, errors):
        self.errors = errors
