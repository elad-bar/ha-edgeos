from __future__ import annotations

from asyncio import sleep
from datetime import datetime, timedelta
import json
import logging
import sys
from typing import Any

from aiohttp import ClientSession, CookieJar

from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.dispatcher import async_dispatcher_send

from ..common.connectivity_status import ConnectivityStatus
from ..common.consts import (
    API_DATA,
    API_DATA_COOKIES,
    API_DATA_INTERFACES,
    API_DATA_LAST_UPDATE,
    API_DATA_PRODUCT,
    API_DATA_SAVE,
    API_DATA_SESSION_ID,
    API_DATA_SYSTEM,
    API_DELETE,
    API_GET,
    API_SET,
    API_URL_DATA,
    API_URL_DATA_SUBSET,
    API_URL_HEARTBEAT,
    API_URL_PARAMETER_ACTION,
    API_URL_PARAMETER_BASE_URL,
    API_URL_PARAMETER_SUBSET,
    API_URL_PARAMETER_TIMESTAMP,
    COOKIE_BEAKER_SESSION_ID,
    COOKIE_CSRF_TOKEN,
    COOKIE_PHPSESSID,
    DEFAULT_NAME,
    EMPTY_STRING,
    HEADER_CSRF_TOKEN,
    HEARTBEAT_MAX_AGE,
    MAXIMUM_RECONNECT,
    RESPONSE_ERROR_KEY,
    RESPONSE_FAILURE_CODE,
    RESPONSE_OUTPUT,
    RESPONSE_SUCCESS_KEY,
    SIGNAL_API_STATUS,
    SIGNAL_DATA_CHANGED,
    STRING_DASH,
    STRING_UNDERSCORE,
    SYSTEM_DATA_DISABLE,
    TRUE_STR,
    UPDATE_DATE_ENDPOINTS,
)
from ..models.config_data import ConfigData
from ..models.edge_os_interface_data import EdgeOSInterfaceData
from ..models.exceptions import SessionTerminatedException

_LOGGER = logging.getLogger(__name__)


class RestAPI:
    _hass: HomeAssistant | None
    data: dict

    _base_url: str | None
    _status: ConnectivityStatus | None
    _session: ClientSession | None
    _entry_id: str | None
    _dispatched_devices: list
    _dispatched_server: bool

    _last_valid: datetime | None

    def __init__(
        self, hass: HomeAssistant, config_data: ConfigData, entry_id: str | None = None
    ):
        try:
            self._hass = hass
            self._support_video_browser_api = False

            self.data = {}
            self._cookies = {}

            self._config_data = config_data

            self._local_async_dispatcher_send = None

            self._status = None

            self._session = None
            self._entry_id = entry_id
            self._dispatched_devices = []
            self._dispatched_server = False
            self._last_valid = None

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(
                f"Failed to load {DEFAULT_NAME} API, error: {ex}, line: {line_number}"
            )

    @property
    def is_connected(self):
        result = self._session is not None

        return result

    @property
    def status(self) -> str | None:
        status = self._status

        return status

    @property
    def _is_home_assistant(self):
        return self._hass is not None

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

    async def _do_nothing(self, _status: ConnectivityStatus):
        pass

    async def initialize(self):
        _LOGGER.info("Initializing Shinobi Server API")

        self._set_status(ConnectivityStatus.Connecting)

        cookie_jar = CookieJar(unsafe=True)

        await self._initialize_session(cookie_jar)

        await self.login()

    async def validate(self):
        await self.initialize()

        await self.login()

    def _get_cookie_data(self, cookie_key):
        cookie_data = None

        if self._cookies is not None:
            cookie_data = self._cookies.get(cookie_key)

        return cookie_data

    def _build_endpoint(
        self,
        endpoint,
        timestamp: str | None = None,
        action: str | None = None,
        subset: str | None = None,
    ):
        data = {
            API_URL_PARAMETER_BASE_URL: self._config_data.api_url,
            API_URL_PARAMETER_TIMESTAMP: timestamp,
            API_URL_PARAMETER_ACTION: action,
            API_URL_PARAMETER_SUBSET: subset,
        }

        url = endpoint.format(**data)

        return url

    async def _async_get(
        self,
        endpoint,
        timestamp: str | None = None,
        action: str | None = None,
        subset: str | None = None,
    ):
        result = None
        message = None
        status = 404

        url = self._build_endpoint(endpoint, timestamp, action, subset)

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

            self._set_status(ConnectivityStatus.Disconnected)

        return result

    def _get_post_headers(self):
        headers = {}
        for header_key in self._session.headers:
            header = self._session.headers.get(header_key)

            if header is not None:
                headers[header_key] = header

        headers[HEADER_CSRF_TOKEN] = self.csrf_token

        return headers

    async def _async_post(self, endpoint, data):
        result = None

        try:
            url = self._build_endpoint(endpoint)

            if self._session is not None:
                headers = self._get_post_headers()
                data_json = json.dumps(data)

                async with self._session.post(
                    url, headers=headers, data=data_json, ssl=False
                ) as response:
                    response.raise_for_status()

                    result = await response.json()

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            message = f"Endpoint: {endpoint}, Error: {ex}, Line: {line_number}"
            _LOGGER.warning(f"Request failed, {message}")

        return result

    async def update(self):
        _LOGGER.debug(f"Updating data from device ({self._config_data.hostname})")

        if self.status == ConnectivityStatus.Failed:
            await self.initialize()

        if self.status == ConnectivityStatus.Connected:
            await self._load_system_data()

            for endpoint in UPDATE_DATE_ENDPOINTS:
                await self._load_general_data(endpoint)

            self.data[API_DATA_LAST_UPDATE] = datetime.now().isoformat()

            self._async_dispatcher_send(SIGNAL_DATA_CHANGED)

    async def login(self):
        try:
            username = self._config_data.username
            password = self._config_data.password

            credentials = {CONF_USERNAME: username, CONF_PASSWORD: password}

            url = self._config_data.api_url

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
                            self.data[API_DATA_PRODUCT] = value.replace(
                                "'", EMPTY_STRING
                            )
                            self.data[API_DATA_SESSION_ID] = self.session_id
                            self.data[API_DATA_COOKIES] = self._cookies

                            self._set_status(ConnectivityStatus.Connected)

                            break
                else:
                    _LOGGER.error("Failed to login, Invalid credentials")

                    if self.beaker_session_id is None and self.session_id is not None:
                        self._set_status(ConnectivityStatus.Failed)
                    else:
                        self._set_status(ConnectivityStatus.InvalidCredentials)

        except SessionTerminatedException:
            self._set_status(ConnectivityStatus.Disconnected)

            raise SessionTerminatedException()

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(f"Failed to login, Error: {ex}, Line: {line_number}")

            self._set_status(ConnectivityStatus.NotFound)

    async def _initialize_session(self, cookie_jar=None):
        try:
            if self._is_home_assistant:
                self._session = async_create_clientsession(
                    hass=self._hass, cookies=self._cookies, cookie_jar=cookie_jar
                )

            else:
                self._session = ClientSession(
                    cookies=self._cookies, cookie_jar=cookie_jar
                )

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.warning(
                f"Failed to initialize session, Error: {str(ex)}, Line: {line_number}"
            )

            self._set_status(ConnectivityStatus.Failed)

    def _set_status(self, status: ConnectivityStatus):
        if status != self._status:
            log_level = ConnectivityStatus.get_log_level(status)

            _LOGGER.log(
                log_level,
                f"Status changed from '{self._status}' to '{status}'",
            )

            self._status = status

            self._async_dispatcher_send(SIGNAL_API_STATUS, status)

    def set_local_async_dispatcher_send(self, callback):
        self._local_async_dispatcher_send = callback

    def _async_dispatcher_send(self, signal: str, *args: Any) -> None:
        if self._hass is None:
            self._local_async_dispatcher_send(signal, None, *args)

        else:
            async_dispatcher_send(self._hass, signal, self._entry_id, *args)

    async def async_send_heartbeat(self, max_age=HEARTBEAT_MAX_AGE):
        ts = None

        try:
            if self.status == ConnectivityStatus.Connected:
                ts = datetime.now()
                current_invocation = datetime.now() - self._last_valid
                if current_invocation > timedelta(seconds=max_age):
                    current_ts = str(int(ts.timestamp()))

                    response = await self._async_get(
                        API_URL_HEARTBEAT, timestamp=current_ts
                    )

                    if response is not None:
                        _LOGGER.debug(f"Heartbeat response: {response}")

                        self._last_valid = ts
            else:
                _LOGGER.debug(
                    "Ignoring request to send heartbeat, Reason: closed session"
                )
        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(
                f"Failed to perform heartbeat, Error: {ex}, Line: {line_number}"
            )

        is_valid = ts is not None and self._last_valid == ts

        if not is_valid:
            self._set_status(ConnectivityStatus.Disconnected)

    async def _load_system_data(self):
        try:
            if self.status == ConnectivityStatus.Connected:
                result_json = await self._async_get(API_URL_DATA, action=API_GET)

                if result_json is not None:
                    if RESPONSE_SUCCESS_KEY in result_json:
                        success_key = str(
                            result_json.get(RESPONSE_SUCCESS_KEY, "")
                        ).lower()

                        if success_key == TRUE_STR:
                            if API_GET.upper() in result_json:
                                self.data[API_DATA_SYSTEM] = result_json.get(
                                    API_GET.upper(), {}
                                )
                        else:
                            error_message = result_json[RESPONSE_ERROR_KEY]
                            _LOGGER.error(f"Failed, Error: {error_message}")
                    else:
                        _LOGGER.error("Invalid response, not contain success status")
            else:
                _LOGGER.debug(
                    "Ignoring request to get devices data, Reason: closed session"
                )
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

                data = await self._async_get(
                    API_URL_DATA_SUBSET, action=API_DATA, subset=clean_item
                )

                if data is not None:
                    if RESPONSE_SUCCESS_KEY in data:
                        if str(data.get(RESPONSE_SUCCESS_KEY)) == RESPONSE_FAILURE_CODE:
                            error = data.get(RESPONSE_ERROR_KEY, EMPTY_STRING)

                            _LOGGER.error(f"Failed to load {key}, Reason: {error}")
                        else:
                            self.data[key] = data.get(RESPONSE_OUTPUT)
            else:
                _LOGGER.debug(
                    f"Ignoring request to get data of {key}, Reason: closed session"
                )

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(f"Failed to load {key}, Error: {ex}, Line: {line_number}")

    async def set_interface_state(
        self, interface: EdgeOSInterfaceData, is_enabled: bool
    ):
        _LOGGER.info(f"Set state of interface {interface.name} to {is_enabled}")

        modified = False
        endpoint = API_DELETE if is_enabled else API_SET

        data = {
            API_DATA_INTERFACES: {
                interface.interface_type: {interface.name: {SYSTEM_DATA_DISABLE: None}}
            }
        }

        result_json = await self._async_post(endpoint, data)

        if result_json is not None:
            set_response = result_json.get(API_DATA_SAVE.upper(), {})

            if RESPONSE_SUCCESS_KEY in set_response:
                success_key = str(
                    set_response.get(RESPONSE_SUCCESS_KEY, RESPONSE_FAILURE_CODE)
                ).lower()

                modified = success_key != RESPONSE_FAILURE_CODE

        if not modified:
            _LOGGER.error(
                f"Failed to set state of interface {interface.name} to {is_enabled}"
            )
