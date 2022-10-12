from __future__ import annotations

from asyncio import sleep
import json
import logging
import sys
from typing import Awaitable, Callable

from aiohttp import ClientSession, CookieJar

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from ...configuration.models.config_data import ConfigData
from ...core.api.base_api import BaseAPI
from ...core.helpers.enums import ConnectivityStatus
from ..helpers.const import *
from ..models.edge_os_interface_data import EdgeOSInterfaceData
from ..models.exceptions import SessionTerminatedException

_LOGGER = logging.getLogger(__name__)


class IntegrationAPI(BaseAPI):
    """The Class for handling the data retrieval."""

    _session: ClientSession | None
    _config_data: ConfigData | None

    def __init__(self,
                 hass: HomeAssistant,
                 async_on_data_changed: Callable[[], Awaitable[None]] | None = None,
                 async_on_status_changed: Callable[[ConnectivityStatus], Awaitable[None]] | None = None
                 ):

        super().__init__(hass, async_on_data_changed, async_on_status_changed)

        try:
            self._config_data = None
            self._session = None
            self._cookies = {}
            self._last_valid = None

            self.data = {}

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(
                f"Failed to load Shinobi Video API, error: {ex}, line: {line_number}"
            )

    @property
    def session_id(self):
        session_id = self._get_cookie_data(COOKIE_PHPSESSID)

        return session_id

    @property
    def beaker_session_id(self):
        beaker_session_id = self._get_cookie_data(COOKIE_BEAKER_SESSION_ID)

        return beaker_session_id

    @property
    def csrf_token(self):
        csrf_token = self._get_cookie_data(COOKIE_CSRF_TOKEN)

        return csrf_token

    @property
    def cookies_data(self):
        return self._cookies

    async def terminate(self):
        await self.set_status(ConnectivityStatus.Disconnected)

    async def initialize(self, config_data: ConfigData):
        _LOGGER.info("Initializing API")

        try:
            self._config_data = config_data

            cookie_jar = CookieJar(unsafe=True)

            if self.hass is None:
                self._session = ClientSession(cookie_jar=cookie_jar)
            else:
                self._session = async_create_clientsession(
                    hass=self.hass, cookies=self._cookies, cookie_jar=cookie_jar,
                )

            await self._login()

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(
                f"Failed to initialize API, error: {ex}, line: {line_number}"
            )

    async def validate(self, data: dict | None = None):
        config_data = ConfigData.from_dict(data)

        await self.initialize(config_data)

    def _get_cookie_data(self, cookie_key):
        cookie_data = None

        if self._cookies is not None:
            cookie_data = self._cookies.get(cookie_key)

        return cookie_data

    async def _login(self):
        await self.set_status(ConnectivityStatus.Connecting)

        try:
            username = self._config_data.username
            password = self._config_data.password

            credentials = {CONF_USERNAME: username, CONF_PASSWORD: password}

            url = self._config_data.url

            if self._session.closed:
                raise SessionTerminatedException()

            async with self._session.post(url, data=credentials, ssl=False) as response:
                all_cookies = self._session.cookie_jar.filter_cookies(response.url)

                for key, cookie in all_cookies.items():
                    self._cookies[cookie.key] = cookie.value

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
                            self.data[API_DATA_PRODUCT] = value.replace("'", EMPTY_STRING)
                            self.data[API_DATA_SESSION_ID] = self.session_id
                            self.data[API_DATA_COOKIES] = self._cookies

                            await self.set_status(ConnectivityStatus.Connected)

                            break
                else:
                    _LOGGER.error(f"Failed to login, Invalid credentials")

                    if self.beaker_session_id is None and self.session_id is not None:
                        await self.set_status(ConnectivityStatus.Failed)
                    else:
                        await self.set_status(ConnectivityStatus.InvalidCredentials)

        except SessionTerminatedException:
            await self.set_status(ConnectivityStatus.Disconnected)

            raise SessionTerminatedException()

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(f"Failed to login, Error: {ex}, Line: {line_number}")

            await self.set_status(ConnectivityStatus.NotFound)

    async def _async_get(self, url):
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

        if not status < 400:
            if retry_attempt > 1:
                message = f"{message}, Retry attempt #{retry_attempt}"

            _LOGGER.warning(f"Request failed, {message}")

            await self.set_status(ConnectivityStatus.Disconnected)

        return result

    def _get_post_headers(self):
        headers = {}
        for header_key in self._session.headers:
            header = self._session.headers.get(header_key)

            if header is not None:
                headers[header_key] = header

        headers[HEADER_CSRF_TOKEN] = self.csrf_token

        return headers

    async def _async_post(self, url, data):
        result = None

        try:
            if self._session is not None:
                headers = self._get_post_headers()
                data_json = json.dumps(data)

                async with self._session.post(url, headers=headers, data=data_json, ssl=False) as response:
                    response.raise_for_status()

                    result = await response.json()

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            message = f"URL: {url}, Error: {ex}, Line: {line_number}"
            _LOGGER.warning(f"Request failed, {message}")

        return result

    async def async_send_heartbeat(self, max_age=HEARTBEAT_MAX_AGE):
        ts = None

        try:
            if self.status == ConnectivityStatus.Connected:
                ts = datetime.now()
                current_invocation = datetime.now() - self._last_valid
                if current_invocation > timedelta(seconds=max_age):
                    current_ts = str(int(ts.timestamp()))

                    heartbeat_req_url = self._get_edge_os_api_endpoint(
                        API_HEARTBEAT
                    )
                    heartbeat_req_full_url = API_URL_HEARTBEAT_TEMPLATE.format(
                        heartbeat_req_url, current_ts
                    )

                    response = await self._async_get(heartbeat_req_full_url)

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

        if not is_valid:
            await self.set_status(ConnectivityStatus.Disconnected)

    async def async_update(self):
        try:
            await self._load_system_data()

            for endpoint in UPDATE_DATE_ENDPOINTS:
                await self._load_general_data(endpoint)

            self.data[API_DATA_LAST_UPDATE] = datetime.now().isoformat()

            await self.fire_data_changed_event()
        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(f"Failed to extract WS data, Error: {ex}, Line: {line_number}")

    async def _load_system_data(self):
        try:
            if self.status == ConnectivityStatus.Connected:
                get_req_url = self._get_edge_os_api_endpoint(API_GET)

                result_json = await self._async_get(get_req_url)

                if result_json is not None:
                    if RESPONSE_SUCCESS_KEY in result_json:
                        success_key = str(
                            result_json.get(RESPONSE_SUCCESS_KEY, "")
                        ).lower()

                        if success_key == TRUE_STR:
                            if API_GET.upper() in result_json:
                                self.data[API_DATA_SYSTEM] = result_json.get(API_GET.upper(), {})
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

    async def _load_general_data(self, key):
        try:
            if self.status == ConnectivityStatus.Connected:
                _LOGGER.debug(f"Loading {key} data")

                clean_item = key.replace(STRING_DASH, STRING_UNDERSCORE)
                data_req_url = self._get_edge_os_api_endpoint(API_DATA)
                data_req_full_url = API_URL_DATA_TEMPLATE.format(
                    data_req_url, clean_item
                )

                data = await self._async_get(data_req_full_url)

                if data is not None:
                    if RESPONSE_SUCCESS_KEY in data:
                        if str(data.get(RESPONSE_SUCCESS_KEY)) == RESPONSE_FAILURE_CODE:
                            error = data.get(RESPONSE_ERROR_KEY, EMPTY_STRING)

                            _LOGGER.error(f"Failed to load {key}, Reason: {error}")
                        else:
                            self.data[key] = data.get(RESPONSE_OUTPUT)
            else:
                _LOGGER.warning(f"Get data of {key} not ran due to closed session")

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(f"Failed to load {key}, Error: {ex}, Line: {line_number}")

    async def set_interface_state(self, interface: EdgeOSInterfaceData, is_enabled: bool):
        _LOGGER.info(f"Set state of interface {interface.name} to {is_enabled}")

        modified = False
        endpoint = API_DELETE if is_enabled else API_SET

        data = {
            API_DATA_INTERFACES: {
                interface.interface_type: {
                    interface.name: {
                        SYSTEM_DATA_DISABLE: None
                    }
                }
            }
        }

        get_req_url = self._get_edge_os_api_endpoint(endpoint)

        result_json = await self._async_post(get_req_url, data)

        if result_json is not None:
            set_response = result_json.get(API_DATA_SAVE.upper(), {})

            if RESPONSE_SUCCESS_KEY in set_response:
                success_key = str(
                    set_response.get(RESPONSE_SUCCESS_KEY, RESPONSE_FAILURE_CODE)
                ).lower()

                modified = success_key != RESPONSE_FAILURE_CODE

        if not modified:
            _LOGGER.error(f"Failed to set state of interface {interface.name} to {is_enabled}")

    def _get_edge_os_api_endpoint(self, endpoint):
        url = API_URL.format(self._config_data.url, endpoint)

        return url
