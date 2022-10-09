from __future__ import annotations

from typing import Awaitable, Callable

from homeassistant.core import HomeAssistant

from ..helpers.enums import ConnectivityStatus


class BaseAPI:
    """The Class for handling the data retrieval."""

    hass: HomeAssistant
    status: ConnectivityStatus
    data: dict
    onDataChangedAsync: Callable[[], Awaitable[None]] | None = None
    onStatusChangedAsync: Callable[[ConnectivityStatus], Awaitable[None]] | None = None

    def __init__(self,
                 hass: HomeAssistant,
                 async_on_data_changed: Callable[[], Awaitable[None]] | None = None,
                 async_on_status_changed: Callable[[ConnectivityStatus], Awaitable[None]] | None = None
                 ):

        self.hass = hass
        self.status = ConnectivityStatus.NotConnected
        self.data = {}
        self.onDataChangedAsync = async_on_data_changed
        self.onStatusChangedAsync = async_on_status_changed

    async def validate(self, data: dict | None = None):
        pass

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
