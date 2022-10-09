from homeassistant.exceptions import HomeAssistantError


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
