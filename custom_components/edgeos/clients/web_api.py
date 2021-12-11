"""
This component provides support for Home Automation Manager (HAM).
For more details about this component, please refer to the documentation at
https://home-assistant.io/components/edgeos/
"""
from asyncio import sleep
import logging
import sys
from typing import Optional

from aiohttp import ClientSession, CookieJar

from homeassistant.helpers.aiohttp_client import async_create_clientsession

from ..helpers.const import *
from ..managers.configuration_manager import ConfigManager
from ..models.exceptions import LoginException, SessionTerminatedException
from .web_socket import EdgeOSWebSocket

REQUIREMENTS = ["aiohttp"]

_LOGGER = logging.getLogger(__name__)


class EdgeOSWebAPI:
    def __init__(
        self,
        hass,
        config_manager: ConfigManager,
        disconnection_handler=None,
        ws: Optional[EdgeOSWebSocket] = None,
    ):
        self._config_manager = config_manager
        self._last_update = datetime.now()
        self._session: Optional[ClientSession] = None

        self._last_valid = EMPTY_LAST_VALID
        self._hass = hass
        self._is_connected = False
        self._cookies = {}

        self._product = PRODUCT_NAME
        self._disconnection_handler = disconnection_handler

        self._disconnections = 0

        self._ws = ws

    async def initialize(self):
        cookie_jar = CookieJar(unsafe=True)

        if self._hass is None:
            self._session = ClientSession(cookie_jar=cookie_jar)
        else:
            self._session = async_create_clientsession(
                hass=self._hass, cookies=self._cookies, cookie_jar=cookie_jar,
            )

    @property
    def is_initialized(self):
        return self._session is not None and not self._session.closed

    @property
    def is_connected(self):
        return self._is_connected

    @property
    def product(self):
        return self._product

    @property
    def session_id(self):
        session_id = self.get_cookie_data(COOKIE_PHPSESSID)

        return session_id

    @property
    def beaker_session_id(self):
        beaker_session_id = self.get_cookie_data(COOKIE_BEAKER_SESSION_ID)

        return beaker_session_id

    @property
    def cookies_data(self):
        return self._cookies

    def get_cookie_data(self, cookie_key):
        cookie_data = None

        if self._cookies is not None:
            cookie_data = self._cookies.get(cookie_key)

        return cookie_data

    async def login(self, throw_exception=False):
        logged_in = False

        try:
            username = self._config_manager.data.username
            password = self._config_manager.data.password_clear_text

            credentials = {CONF_USERNAME: username, CONF_PASSWORD: password}

            url = self._config_manager.data.url

            if self._session.closed:
                raise SessionTerminatedException()

            async with self._session.post(url, data=credentials, ssl=False) as response:
                all_cookies = self._session.cookie_jar.filter_cookies(response.url)

                for key, cookie in all_cookies.items():
                    self._cookies[cookie.key] = cookie.value

                status_code = response.status

                response.raise_for_status()

                logged_in = (
                    self.beaker_session_id is not None
                    and self.beaker_session_id == self.session_id
                )

                if logged_in:
                    html = await response.text()
                    html_lines = html.splitlines()
                    for line in html_lines:
                        if "EDGE.DeviceModel" in line:
                            line_parts = line.split(" = ")
                            value = line_parts[len(line_parts) - 1]
                            self._product = value.replace("'", "")
                else:
                    _LOGGER.error(f"Failed to login, Invalid credentials")

                    if self.beaker_session_id is None and self.session_id is not None:
                        status_code = 500
                    else:
                        status_code = 403
        except SessionTerminatedException:
            raise SessionTerminatedException()

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(f"Failed to login, Error: {ex}, Line: {line_number}")

            status_code = 404

        if throw_exception and status_code is not None and status_code >= 400:
            raise LoginException(status_code)

        return logged_in

    async def async_get(self, url):
        result = None
        message = None
        status = 404

        retry_attempt = 0
        while retry_attempt < MAXIMUM_RECONNECT:
            if retry_attempt > 0:
                await sleep(1)

            retry_attempt = retry_attempt + 1

            try:
                if self._session is not None:
                    async with self._session.get(url, ssl=False) as response:
                        status = response.status

                        message = (
                            f"URL: {url}, Status: {response.reason} ({response.status})"
                        )

                        if status < 400:
                            result = await response.json()
                            break
                        elif status == 403:
                            self._session = None
                            self._cookies = {}

                            break

            except Exception as ex:
                exc_type, exc_obj, tb = sys.exc_info()
                line_number = tb.tb_lineno
                message = f"URL: {url}, Error: {ex}, Line: {line_number}"

        valid_response = status < 400

        self._is_connected = valid_response

        if retry_attempt > 1:
            message = f"{message}, Retry attempt #{retry_attempt}"

        if valid_response:
            self._last_update = datetime.now()
            _LOGGER.debug(message)

        else:
            _LOGGER.warning(f"Request failed, {message}")

            if self._ws is not None:
                self._ws.disconnect()

        return result

    @property
    def last_update(self):
        result = self._last_update

        return result

    async def async_send_heartbeat(self, max_age=HEARTBEAT_MAX_AGE):
        ts = None

        try:
            if self.is_initialized:
                ts = datetime.now()
                current_invocation = datetime.now() - self._last_valid
                if current_invocation > timedelta(seconds=max_age):
                    current_ts = str(int(ts.timestamp()))

                    heartbeat_req_url = self.get_edgeos_api_endpoint(
                        EDGEOS_API_HEARTBREAT
                    )
                    heartbeat_req_full_url = API_URL_HEARTBEAT_TEMPLATE.format(
                        heartbeat_req_url, current_ts
                    )

                    response = await self.async_get(heartbeat_req_full_url)

                    if response is not None:
                        _LOGGER.debug(f"Heartbeat response: {response}")

                        self._last_valid = ts
            else:
                _LOGGER.warning(f"Heartbeat not ran due to closed session")
        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(
                f"Failed to perform heartbeat, Error: {ex}, Line: {line_number}"
            )

        is_valid = ts is not None and self._last_valid == ts

        return is_valid

    async def get_devices_data(self):
        result = None

        try:
            if self.is_initialized:
                get_req_url = self.get_edgeos_api_endpoint(EDGEOS_API_GET)

                result_json = await self.async_get(get_req_url)

                if result_json is not None:
                    if RESPONSE_SUCCESS_KEY in result_json:
                        success_key = str(
                            result_json.get(RESPONSE_SUCCESS_KEY, "")
                        ).lower()

                        if success_key == TRUE_STR:
                            if EDGEOS_API_GET.upper() in result_json:
                                result = result_json.get(EDGEOS_API_GET.upper(), {})
                        else:
                            error_message = result_json[RESPONSE_ERROR_KEY]
                            _LOGGER.error(f"Failed, Error: {error_message}")
                    else:
                        _LOGGER.error("Invalid response, not contain success status")
            else:
                _LOGGER.warning(f"Get devices data not ran due to closed session")
        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(
                f"Failed to get devices data, Error: {ex}, Line: {line_number}"
            )

        return result

    async def get_general_data(self, item):
        result = None

        try:
            if self.is_initialized:
                clean_item = item.replace(STRING_DASH, STRING_UNDERSCORE)
                data_req_url = self.get_edgeos_api_endpoint(EDGEOS_API_DATA)
                data_req_full_url = API_URL_DATA_TEMPLATE.format(
                    data_req_url, clean_item
                )

                data = await self.async_get(data_req_full_url)

                if data is not None:
                    if RESPONSE_SUCCESS_KEY in data:
                        if str(data.get(RESPONSE_SUCCESS_KEY)) == RESPONSE_FAILURE_CODE:
                            error = data.get(RESPONSE_ERROR_KEY, EMPTY_STRING)

                            _LOGGER.error(f"Failed to load {item}, Reason: {error}")
                            result = None
                        else:
                            result = data.get(RESPONSE_OUTPUT)
            else:
                _LOGGER.warning(f"Get data of {item} not ran due to closed session")

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(f"Failed to load {item}, Error: {ex}, Line: {line_number}")
            result = None

        return result

    def get_edgeos_api_endpoint(self, controller):
        url = EDGEOS_API_URL.format(self._config_manager.data.url, controller)

        return url
