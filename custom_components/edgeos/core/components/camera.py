"""
Support for camera.
"""
from __future__ import annotations

from abc import ABC
import asyncio
from datetime import datetime
import logging
import sys

import aiohttp
import async_timeout

from homeassistant.components.camera import (
    DEFAULT_CONTENT_TYPE,
    Camera,
    CameraEntityFeature,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import TemplateError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv

from ..helpers.const import (
    ATTR_MODE_RECORD,
    ATTR_STREAM_FPS,
    CONF_MOTION_DETECTION,
    CONF_STILL_IMAGE_URL,
    CONF_STREAM_SOURCE,
    DOMAIN_CAMERA,
    EMPTY_STRING,
    SINGLE_FRAME_PS,
)
from ..models.base_entity import BaseEntity
from ..models.entity_data import EntityData

_LOGGER = logging.getLogger(__name__)


class CoreCamera(Camera, BaseEntity, ABC):
    """Camera"""

    def __init__(self, hass, device_info):
        super().__init__()
        self.hass = hass
        self._still_image_url = None
        self._stream_source = None
        self._frame_interval = 0
        self._supported_features = 0
        self.content_type = DEFAULT_CONTENT_TYPE
        self._auth = None
        self._last_url = None
        self._last_image = None
        self.verify_ssl = False
        self._is_recording_state = None

    def initialize(
        self,
        hass: HomeAssistant,
        entity: EntityData,
        current_domain: str,
        DOMAIN_STREAM=None,
    ):
        super().initialize(hass, entity, current_domain)

        try:
            if self.ha is None:
                _LOGGER.warning("Failed to initialize CoreCamera without HA manager")
                return

            config_data = self.ha.config_data

            username = config_data.username
            password = config_data.password

            fps_str = entity.details.get(ATTR_STREAM_FPS, SINGLE_FRAME_PS)

            fps = SINGLE_FRAME_PS if fps_str == EMPTY_STRING else int(float(fps_str))

            stream_source = entity.attributes.get(CONF_STREAM_SOURCE)

            snapshot = entity.attributes.get(CONF_STILL_IMAGE_URL)

            still_image_url_template = cv.template(snapshot)

            self._still_image_url = still_image_url_template
            self._still_image_url.hass = hass

            self._stream_source = stream_source
            self._frame_interval = SINGLE_FRAME_PS / fps

            self._is_recording_state = self.entity.details.get(ATTR_MODE_RECORD)
            self._attr_is_streaming = stream_source is not None

            if self._stream_source:
                self._attr_supported_features = CameraEntityFeature.STREAM
            else:
                self._attr_supported_features = CameraEntityFeature(0)

            if username and password:
                self._auth = aiohttp.BasicAuth(username, password=password)

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(
                f"Failed to initialize CoreCamera instance, Error: {ex}, Line: {line_number}"
            )

    @property
    def is_recording(self) -> bool:
        return self.entity.state == self._is_recording_state

    @property
    def motion_detection_enabled(self):
        return self.entity.details.get(CONF_MOTION_DETECTION, False)

    @property
    def frame_interval(self):
        """Return the interval between frames of the mjpeg stream."""
        return self._frame_interval

    def camera_image(
        self, width: int | None = None, height: int | None = None
    ) -> bytes | None:
        """Return bytes of camera image."""
        return asyncio.run_coroutine_threadsafe(
            self.async_camera_image(), self.hass.loop
        ).result()

    async def async_camera_image(
        self, width: int | None = None, height: int | None = None
    ) -> bytes | None:
        """Return a still image response from the camera."""
        try:
            url = self._still_image_url.async_render()
        except TemplateError as err:
            _LOGGER.error(
                f"Error parsing template {self._still_image_url}, Error: {err}"
            )
            return self._last_image

        try:
            ws = async_get_clientsession(self.hass, verify_ssl=self.verify_ssl)
            async with async_timeout.timeout(10):
                url = f"{url}?ts={datetime.now().timestamp()}"
                response = await ws.get(url, auth=self._auth)

            self._last_image = await response.read()

        except asyncio.TimeoutError:
            _LOGGER.error(f"Timeout getting camera image from {self.name}")
            return self._last_image

        except aiohttp.ClientError as err:
            _LOGGER.error(
                f"Error getting new camera image from {self.name}, Error: {err}"
            )
            return self._last_image

        self._last_url = url
        return self._last_image

    async def stream_source(self):
        """Return the source of the stream."""
        return self._stream_source

    async def async_enable_motion_detection(self) -> None:
        """Enable motion detection in the camera."""
        if self.motion_detection_enabled:
            _LOGGER.error(f"{self.name} - motion detection already enabled'")

        else:
            await self.ha.async_core_entity_enable_motion_detection(self.entity)

    async def async_disable_motion_detection(self) -> None:
        """Disable motion detection in camera."""
        if self.motion_detection_enabled:
            await self.ha.async_core_entity_disable_motion_detection(self.entity)

        else:
            _LOGGER.error(f"{self.name} - motion detection already disabled'")

    @staticmethod
    def get_component(hass: HomeAssistant, entity: EntityData):
        camera = CoreCamera(hass, entity.details)
        camera.initialize(hass, entity, DOMAIN_CAMERA)

        return camera

    @staticmethod
    def get_domain():
        return DOMAIN_CAMERA
