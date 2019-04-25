import sys
import logging
import requests
from time import sleep
import urllib3

from homeassistant.const import (CONF_USERNAME, CONF_PASSWORD)

from .const import *

_LOGGER = logging.getLogger(__name__)


class EdgeOSWebLogin(requests.Session):
    def __init__(self, host, is_ssl, username, password):
        requests.Session.__init__(self)

        self._credentials = {
            CONF_USERNAME: username,
            CONF_PASSWORD: password
        }

        self._is_ssl = is_ssl

        protocol = PROTOCOL_UNSECURED
        if self._is_ssl:
            protocol = PROTOCOL_SECURED

        self._edgeos_url = API_URL_TEMPLATE.format(protocol, host)

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

    def login(self):
        try:
            if self._is_ssl:
                login_response = self.post(self._edgeos_url, data=self._credentials, verify=False)
            else:
                login_response = self.post(self._edgeos_url, data=self._credentials)

            login_response.raise_for_status()

            _LOGGER.debug("Sleeping 2 to make sure the session id is in the filesystem")
            sleep(2)

            return True
        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(f'Failed to login, Error: {ex}, Line: {line_number}')

        return False
