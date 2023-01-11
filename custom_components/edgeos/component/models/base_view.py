from __future__ import annotations

from collections.abc import Callable
import logging

from homeassistant.components.http import HomeAssistantView

from ...core.helpers.const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class EdgeOSBaseView(HomeAssistantView):
    name: str
    _prefix: str
    _get_data_callback: Callable[[str], dict]

    def __init__(
        self,
        hass,
        prefix: str,
        get_data_callback: Callable[[str], dict],
        entry_id: str | None = None,
    ):
        self.data = None
        self._entry_id = entry_id
        self._hass = hass
        self._get_data_callback = get_data_callback
        self._prefix = prefix

        if entry_id is None:
            self.url = f"/api/{DOMAIN}/{prefix}"

        else:
            self.url = f"/api/{DOMAIN}/{entry_id}/{prefix}"

        self.name = self.url.replace("/", ":")

    async def get(self, request):
        return self.json(self._get_data_callback(self._prefix))
