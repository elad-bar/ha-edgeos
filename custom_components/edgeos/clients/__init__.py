from homeassistant.exceptions import HomeAssistantError


class SessionTerminatedException(HomeAssistantError):
    Terminated = True


class LoginException(HomeAssistantError):
    def __init__(self, status_code):
        self._status_code = status_code

    @property
    def status_code(self):
        return self._status_code
