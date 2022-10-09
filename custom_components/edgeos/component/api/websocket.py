"""
websocket.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import sys
from typing import Awaitable, Callable
from urllib.parse import urlparse

import aiohttp
from aiohttp import ClientSession

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from ...component.helpers.const import *
from ...configuration.models.config_data import ConfigData
from ...core.api.base_api import BaseAPI
from ...core.helpers.enums import ConnectivityStatus

REQUIREMENTS = ["aiohttp"]

_LOGGER = logging.getLogger(__name__)


class IntegrationWS(BaseAPI):
    _session: ClientSession | None
    _config_data: ConfigData | None
    _api_data: dict
    _can_log_messages: bool
    _previous_message: dict | None
    _ws_handlers: dict
    _messages_received: float
    _messages_ignored: float

    def __init__(self,
                 hass: HomeAssistant,
                 async_on_data_changed: Callable[[], Awaitable[None]] | None = None,
                 async_on_status_changed: Callable[[ConnectivityStatus], Awaitable[None]] | None = None
                 ):

        super().__init__(hass, async_on_data_changed, async_on_status_changed)

        self._config_data = None
        self._session = None
        self._ws = None
        self._api_data = {}
        self._remove_async_track_time = None
        self._ws_handlers = self._get_ws_handlers()
        self._can_log_messages: bool = False
        self._messages_received = 0
        self._messages_ignored = 0
        self._previous_message = None
        self.data = {
            EXPORT_KEY: {},
            INTERFACES: {},
        }

    @property
    def _api_session_id(self):
        api_session_id = self._api_data.get(API_DATA_SESSION_ID)

        return api_session_id

    @property
    def _api_cookies(self):
        api_cookies = self._api_data.get(API_DATA_COOKIES)

        return api_cookies

    @property
    def _ws_url(self):
        url = urlparse(self._config_data.url)

        ws_url = WEBSOCKET_URL_TEMPLATE.format(url.netloc)

        return ws_url

    async def update_api_data(self, api_data: dict, can_log_messages: bool):
        self._api_data = api_data
        self._can_log_messages = can_log_messages

    async def initialize(self, config_data: ConfigData):
        self._config_data = config_data

        _LOGGER.debug(f"Initializing WebSocket connection")
        await self.set_status(ConnectivityStatus.Connecting)

        previous_status = self.status

        try:
            if self.hass is None:
                self._session = ClientSession(cookies=self._api_cookies)
            else:
                self._session = async_create_clientsession(
                    hass=self.hass, cookies=self._api_cookies
                )

        except Exception as ex:
            _LOGGER.warning(f"Failed to create web socket session, Error: {str(ex)}")

        try:
            url = self._ws_url

            async with self._session.ws_connect(
                url,
                ssl=False,
                autoclose=True,
                max_msg_size=MAX_MSG_SIZE,
                timeout=SCAN_INTERVAL_WS_TIMEOUT,
            ) as ws:

                await self.set_status(ConnectivityStatus.Connected)

                self._ws = ws

                await self._listen()

        except Exception as ex:
            if self._session is not None and self._session.closed:
                _LOGGER.info(f"WS Session closed")
            else:
                exc_type, exc_obj, tb = sys.exc_info()
                line_number = tb.tb_lineno

                _LOGGER.warning(f"Failed to connect WS, Error: {ex}, Line: {line_number}")

        if self.status == ConnectivityStatus.Connected:
            await self.set_status(ConnectivityStatus.NotConnected)

            _LOGGER.info("WS Connection terminated")

        else:
            if previous_status == ConnectivityStatus.NotConnected:
                await asyncio.sleep(RECONNECT_INTERVAL)

                await self.fire_status_changed_event()

    async def terminate(self):
        if self._remove_async_track_time is not None:
            self._remove_async_track_time()
            self._remove_async_track_time = None

        await self.set_status(ConnectivityStatus.Disconnected)

    async def async_send_heartbeat(self):
        _LOGGER.debug(f"Keep alive message sent")

        if self.status == ConnectivityStatus.Connected:
            content = "{CLIENT_PING}"

            _LOGGER.debug(f"Keep alive data to be sent: {content}")

            await self._ws.send_str(content)

    async def _listen(self):
        try:
            _LOGGER.info(f"Starting to listen connected")

            subscription_data = self._get_subscription_data()
            await self._ws.send_str(subscription_data)

            _LOGGER.info("Subscribed to WS payloads")

            async for msg in self._ws:
                continue_to_next = await self._handle_next_message(msg)

                if (
                    not continue_to_next
                    or self.status != ConnectivityStatus.Connected
                ):
                    break

            _LOGGER.info(f"Stop listening")

        except Exception as ex:
            if self._session is not None and self._session.closed:
                _LOGGER.info(f"Stopped listen, Error: WS Session closed")

            else:
                exc_type, exc_obj, tb = sys.exc_info()
                line_number = tb.tb_lineno

                _LOGGER.warning(f"Stopped listen, Error: {ex}, Line: {line_number}")

    async def _handle_next_message(self, msg):
        _LOGGER.debug(f"Starting to handle next message")
        result = False

        if msg.type in (
            aiohttp.WSMsgType.CLOSE,
            aiohttp.WSMsgType.CLOSED,
            aiohttp.WSMsgType.CLOSING,
        ):
            _LOGGER.info("Connection closed (By Message Close)")

        elif msg.type == aiohttp.WSMsgType.ERROR:
            _LOGGER.warning(f"Connection error, Description: {self._ws.exception()}")

        else:
            if self._can_log_messages:
                _LOGGER.debug(f"New message received: {str(msg)}")

            if msg.data == "close":
                result = False
            else:
                await self.parse_message(msg.data)

                result = True

        return result

    async def parse_message(self, message):
        try:
            self._messages_received += 1

            if self._previous_message is not None:
                message = self._get_corrected_message(message)

            if message is not None:
                message_json = re.sub(BEGINS_WITH_SIX_DIGITS, EMPTY_STRING, message)

                if len(message_json.strip()) > 0:
                    payload_json = json.loads(message_json)

                    await self._message_handler(payload_json)
            else:
                self._messages_ignored += 1

        except ValueError:
            self._messages_ignored += 1

            previous_messages = re.findall(BEGINS_WITH_SIX_DIGITS, message)

            if previous_messages is None or len(previous_messages) == 0:
                _LOGGER.warning("Failed to store partial message for later processing")

            else:
                length = int(previous_messages[0])

                self._previous_message = {
                    "Length": length,
                    "Content": message
                }

                _LOGGER.debug("Store partial message for later processing")

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.warning(f"Parse message failed, Data: {message}, Error: {ex}, Line: {line_number}")

    def _get_corrected_message(self, message):
        original_message = message
        previous_message = self._previous_message.get("Content")
        previous_message_length = self._previous_message.get("Length")

        self._previous_message = None

        message = f"{previous_message}{message}"
        new_message_length = len(message) - len(str(previous_message_length)) - 1

        if new_message_length > previous_message_length:
            _LOGGER.debug(
                f"Ignored partial message, "
                f"Expected {previous_message_length} chars, "
                f"Provided {new_message_length}, "
                f"Content: {message}"
            )

            message = original_message

        else:
            self._messages_ignored -= 1
            _LOGGER.debug("Partial message corrected")

        return message

    def _get_subscription_data(self):
        topics = self._ws_handlers.keys()

        topics_to_subscribe = [{WS_TOPIC_NAME: topic} for topic in topics]
        topics_to_unsubscribe = []

        data = {
            WS_TOPIC_SUBSCRIBE: topics_to_subscribe,
            WS_TOPIC_UNSUBSCRIBE: topics_to_unsubscribe,
            WS_SESSION_ID: self._api_session_id,
        }

        content = json.dumps(data, separators=(STRING_COMMA, STRING_COLON))
        content_length = len(content)
        data = f"{content_length}\n{content}"

        _LOGGER.debug(f"Subscription data to be sent: {data}")

        return data

    def _get_ws_handlers(self) -> dict:
        ws_handlers = {
            EXPORT_KEY: self._handle_export,
            INTERFACES_KEY: self._handle_interfaces,
            SYSTEM_STATS_KEY: self._handle_system_stats,
            DISCOVER_KEY: self._handle_discover,
        }

        return ws_handlers

    async def _message_handler(self, payload=None):
        try:
            if payload is not None:
                for key in payload:
                    _LOGGER.debug(f"Running parser of {key}")

                    data = payload.get(key)
                    handler = self._ws_handlers.get(key)

                    if handler is None:
                        _LOGGER.error(f"Handler not found for {key}")
                    else:
                        handler(data)

                        await self.fire_data_changed_event()
        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(
                f"Failed to handle WS message, Error: {ex}, Line: {line_number}"
            )

    def _handle_export(self, data):
        try:
            _LOGGER.debug(f"Handle {EXPORT_KEY} data")

            if data is None or data == "":
                _LOGGER.debug(f"{EXPORT_KEY} is empty")
                return

            for device_ip in data:
                device_data = data.get(device_ip)

                if device_data is not None:
                    traffic: dict = {}

                    for item in DEVICE_SERVICES_STATS_MAP:
                        traffic[item] = float(0)

                    for service in device_data:
                        service_data = device_data.get(service, {})
                        for item in service_data:
                            current_value = traffic.get(item, 0)
                            service_data_item_value = 0

                            if item in service_data and service_data[item] != "":
                                service_data_item_value = float(service_data[item])

                            traffic_value = current_value + service_data_item_value

                            traffic[item] = traffic_value

                    self.data[EXPORT_KEY][device_ip] = traffic

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(
                f"Failed to load {EXPORT_KEY}, Error: {ex}, Line: {line_number}"
            )

    def _handle_interfaces(self, data):
        try:
            _LOGGER.debug(f"Handle {INTERFACES_KEY} data")

            if data is None or data == "":
                _LOGGER.debug(f"{INTERFACES_KEY} is empty")
                return

            for name in data:
                interface_data = data.get(name)

                interface = {}

                for item in interface_data:
                    item_data = interface_data.get(item)

                    if ADDRESS_LIST == item:
                        interface[item] = item_data

                    elif INTERFACES_STATS == item:
                        for stats_item in INTERFACES_STATS_MAP:
                            interface[stats_item] = float(item_data.get(stats_item))

                    else:
                        if item in INTERFACES_MAIN_MAP:
                            interface[item] = item_data

                self.data[INTERFACES_KEY][name] = interface

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(
                f"Failed to load {INTERFACES_KEY}, Error: {ex}, Line: {line_number}"
            )

    def _handle_system_stats(self, data):
        try:
            _LOGGER.debug(f"Handle {SYSTEM_STATS_KEY} data")

            if data is None or data == "":
                _LOGGER.debug(f"{SYSTEM_STATS_KEY} is empty")
                return

            self.data[SYSTEM_STATS_KEY] = data
        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(
                f"Failed to load {SYSTEM_STATS_KEY}, Error: {ex}, Line: {line_number}"
            )

    def _handle_discover(self, data):
        try:
            _LOGGER.debug(f"Handle {DISCOVER_KEY} data")

            if data is None or data == "":
                _LOGGER.debug(f"{DISCOVER_KEY} is empty")
                return

            devices_data = data.get(DEVICE_LIST, [])
            result = {}

            for device_data in devices_data:
                for key in DISCOVER_DEVICE_ITEMS:
                    device_data_item = device_data.get(key, {})

                    if key == ADDRESS_LIST:
                        discover_addresses = {}

                        for address in device_data_item:
                            hw_addr = address.get(ADDRESS_HWADDR)
                            ipv4 = address.get(ADDRESS_IPV4)

                            discover_addresses[hw_addr] = ipv4

                        result[key] = discover_addresses
                    else:
                        result[key] = device_data_item

            self.data[DISCOVER_KEY] = result
        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(
                f"Failed to load {DISCOVER_KEY}, Original Message: {data}, Error: {ex}, Line: {line_number}"
            )
