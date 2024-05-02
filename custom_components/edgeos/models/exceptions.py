from homeassistant.exceptions import HomeAssistantError

from ..common.connectivity_status import ConnectivityStatus


class LoginError(Exception):
    def __init__(self):
        self.error = "Failed to login"


class AlreadyExistsError(HomeAssistantError):
    title: str

    def __init__(self, title: str):
        self.title = title


class APIValidationException(HomeAssistantError):
    endpoint: str
    status: ConnectivityStatus

    def __init__(self, endpoint: str, status: ConnectivityStatus):
        super().__init__(
            f"API cannot process request to '{endpoint}', Status: {status}"
        )

        self.endpoint = endpoint
        self.status = status


class IncompatibleVersion(HomeAssistantError):
    def __init__(self, version):
        self._version = version

    def __repr__(self):
        return f"Unsupported EdgeOS version ({self._version})"


class SessionTerminatedException(HomeAssistantError):
    Terminated = True


class LoginException(HomeAssistantError):
    def __init__(self, status_code):
        self._status_code = status_code

    @property
    def status_code(self):
        return self._status_code
