import logging
import sys
from time import sleep

import requests
from requests import HTTPError
import urllib3

from homeassistant.exceptions import HomeAssistantError

from ..helpers.const import *

_LOGGER = logging.getLogger(__name__)


class EdgeOSWebLogin(requests.Session):
    def __init__(self, host, username, password):
        requests.Session.__init__(self)

        self._credentials = {CONF_USERNAME: username, CONF_PASSWORD: password}

        self._edgeos_url = API_URL_TEMPLATE.format(host)
        self._product = "EdgeOS Device"

        """ This function turns off InsecureRequestWarnings """
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    @property
    def product(self):
        return self._product

    @property
    def session_id(self):
        session_id = self.get_cookie_data(COOKIE_PHPSESSID)

        return session_id

    @property
    def breaker_session_id(self):
        breaker_session_id = self.get_cookie_data(COOKIE_BEAKER_SESSION_ID)

        return breaker_session_id

    @property
    def cookies_data(self):
        return self.cookies

    def get_cookie_data(self, cookie_key):
        cookie_data = None

        if self.cookies is not None and cookie_key in self.cookies:
            cookie_data = self.cookies[cookie_key]

        return cookie_data

    def login(self, throw_exception=False):
        logged_in = False

        try:
            login_response = self.post(
                self._edgeos_url, data=self._credentials, verify=False
            )

            status_code = login_response.status_code

            login_response.raise_for_status()

            _LOGGER.debug("Sleeping 1 to make sure the session id is in the filesystem")
            sleep(1)

            logged_in = (
                self.breaker_session_id is not None
                and self.breaker_session_id == self.session_id
            )

            if logged_in:
                html = login_response.text
                html_lines = html.splitlines()
                for line in html_lines:
                    if "EDGE.DeviceModel" in line:
                        line_parts = line.split(" = ")
                        value = line_parts[len(line_parts) - 1]
                        self._product = value.replace("'", "")
            else:
                _LOGGER.error(f"Failed to login, Invalid credentials")

                status_code = 403

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(f"Failed to login, Error: {ex}, Line: {line_number}")

            status_code = 404

        if throw_exception and status_code is not None and status_code >= 400:
            raise LoginException(status_code)

        return logged_in


class LoginException(HomeAssistantError):
    def __init__(self, status_code):
        self._status_code = status_code

    @property
    def status_code(self):
        return self._status_code
