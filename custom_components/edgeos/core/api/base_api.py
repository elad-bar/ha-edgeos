from __future__ import annotations

from collections.abc import Awaitable, Callable
import logging
import sys

from aiohttp import ClientSession

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from ..helpers.enums import ConnectivityStatus

_LOGGER = logging.getLogger(__name__)


class BaseAPI:
    """The Class for handling the data retrieval."""

    hass: HomeAssistant
    session: ClientSession | None
    status: ConnectivityStatus
    data: dict
    onDataChangedAsync: Callable[[], Awaitable[None]] | None = None
    onStatusChangedAsync: Callable[[ConnectivityStatus], Awaitable[None]] | None = None

    def __init__(self,
                 hass: HomeAssistant | None,
                 async_on_data_changed: Callable[[], Awaitable[None]] | None = None,
                 async_on_status_changed: Callable[[ConnectivityStatus], Awaitable[None]] | None = None
                 ):

        self.hass = hass
        self.status = ConnectivityStatus.NotConnected
        self.data = {}
        self.onDataChangedAsync = async_on_data_changed
        self.onStatusChangedAsync = async_on_status_changed

        self.session = None

    @property
    def is_home_assistant(self):
        return self.hass is not None

    async def initialize_session(self, cookies=None, cookie_jar=None):
        try:
            if self.is_home_assistant:
                self.session = async_create_clientsession(hass=self.hass, cookies=cookies, cookie_jar=cookie_jar)

            else:
                self.session = ClientSession(cookies=cookies, cookie_jar=cookie_jar)

            await self.login()

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.warning(f"Failed to initialize session, Error: {str(ex)}, Line: {line_number}")

            await self.set_status(ConnectivityStatus.Failed)

    async def login(self):
        _LOGGER.info("Performing login")

        await self.set_status(ConnectivityStatus.Connecting)

    async def validate(self, data: dict | None = None):
        pass

    async def terminate(self):
        self.data = {}

        await self.set_status(ConnectivityStatus.Disconnected)

    async def set_status(self, status: ConnectivityStatus):
        if status != self.status:
            self.status = status

            await self.fire_status_changed_event()

    async def fire_status_changed_event(self):
        if self.onStatusChangedAsync is not None:
            await self.onStatusChangedAsync(self.status)

    async def fire_data_changed_event(self):
        if self.onDataChangedAsync is not None:
            await self.onDataChangedAsync()
