import sys
import logging
import requests
from time import sleep
import urllib3
from homeassistant.exceptions import HomeAssistantError
from requests import HTTPError

from ..helpers.const import *

_LOGGER = logging.getLogger(__name__)


class EdgeOSWebLogin(requests.Session):
    def __init__(self, host, username, password):
        requests.Session.__init__(self)

        self._credentials = {
            CONF_USERNAME: username,
            CONF_PASSWORD: password
        }

        self._edgeos_url = API_URL_TEMPLATE.format(host)

        ''' This function turns off InsecureRequestWarnings '''
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    @property
    def session_id(self):
        session_id = None

        if self.cookies is not None and COOKIE_PHPSESSID in self.cookies:
            session_id = self.cookies[COOKIE_PHPSESSID]

        return session_id

    @property
    def cookies_data(self):
        return self.cookies

    def login(self, throw_exception=False):
        status_code = None
        try:
            login_response = self.post(self._edgeos_url, data=self._credentials, verify=False)

            status_code = login_response.status_code

            login_response.raise_for_status()

            _LOGGER.debug("Sleeping 2 to make sure the session id is in the filesystem")
            sleep(2)

            return True
        except HTTPError as ex_http:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(f'Failed to login, HTTP Error: {ex_http}, Line: {line_number}')

            if throw_exception:
                raise LoginException(status_code)

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(f'Failed to login, Error: {ex}, Line: {line_number}')

            if throw_exception:
                raise LoginException(404)

        return False


class LoginException(HomeAssistantError):
    def __init__(self, status_code):
        self._status_code = status_code

    @property
    def status_code(self):
        return self._status_code
