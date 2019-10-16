"""
This component provides support for Home Automation Manager (HAM).
For more details about this component, please refer to the documentation at
https://home-assistant.io/components/edgeos/
"""
import re
import logging
import json
from urllib.parse import urlparse
import aiohttp

from .const import *

REQUIREMENTS = ['aiohttp']

_LOGGER = logging.getLogger(__name__)


class EdgeOSWebSocket:

    def __init__(self, edgeos_url, topics, edgeos_callback, hass_loop):
        self._last_update = datetime.now()
        self._edgeos_url = edgeos_url
        self._edgeos_callback = edgeos_callback
        self._hass_loop = hass_loop
        self._session_id = None
        self._topics = topics
        self._session = None
        self._log_events = False
        self._ws = None
        self._pending_payloads = []

        self._timeout = SCAN_INTERVAL.seconds

        url = urlparse(self._edgeos_url)

        self._ws_url = WEBSOCKET_URL_TEMPLATE.format(url.netloc)

    async def initialize(self, cookies, session_id):
        _LOGGER.info("Initializing WS connection")

        try:
            await self.close()

            self._session_id = session_id
            self._session = aiohttp.ClientSession(cookies=cookies, loop=self._hass_loop)

        except Exception as ex:
            _LOGGER.warning(f"Failed to create session of EdgeOS WS, Error: {str(ex)}")

        connection_attempt = 1

        while self.is_initialized:
            try:
                _LOGGER.info(f"Connection attempt #{connection_attempt}")

                async with self._session.ws_connect(self._ws_url,
                                                    origin=self._edgeos_url,
                                                    ssl=False,
                                                    max_msg_size=MAX_MSG_SIZE,
                                                    timeout=self._timeout) as ws:
                    self._ws = ws

                    await self.listen()

                connection_attempt = connection_attempt + 1

            except Exception as ex:
                error_message = str(ex)

                if error_message == ERROR_SHUTDOWN:
                    _LOGGER.info(f"{str(error_message)}")

                else:
                    _LOGGER.warning(f"Failed to listen EdgeOS, Error: {str(error_message)}")

        _LOGGER.info("WS Connection terminated")

    def log_events(self, log_event_enabled):
        self._log_events = log_event_enabled

    @property
    def is_initialized(self):
        return self._session is not None and not self._session.closed

    @property
    def last_update(self):
        result = self._last_update

        return result

    def parse_message(self, message):
        parsed = False

        try:
            message = message.replace(NEW_LINE, EMPTY_STRING)
            message = re.sub(BEGINS_WITH_SIX_DIGITS, EMPTY_STRING, message)

            if len(self._pending_payloads) > 0:
                message_previous = ''.join(self._pending_payloads)
                message = f'{message_previous}{message}'

            if len(message) > 0:
                payload_json = json.loads(message)

                self._edgeos_callback(payload_json)
                parsed = True
            else:
                _LOGGER.debug('Parse message skipped (Empty)')

        except Exception as ex:
            _LOGGER.debug(f'Parse message failed due to partial payload, Error: {ex}')

        finally:
            if parsed or len(self._pending_payloads) > MAX_PENDING_PAYLOADS:
                self._pending_payloads = []
            else:
                self._pending_payloads.append(message)

    async def listen(self):
        _LOGGER.info(f"Starting to listen connected")

        subscription_data = self.get_subscription_data()
        await self._ws.send_str(subscription_data)

        _LOGGER.info('Subscribed to WS payloads')

        async for msg in self._ws:
            continue_to_next = self.handle_next_message(msg)

            if not continue_to_next or not self.is_initialized:
                return

        _LOGGER.info(f'Stop listening')

    def handle_next_message(self, msg):
        _LOGGER.debug(f"Starting to handle next message")
        result = False

        if msg.type == aiohttp.WSMsgType.CLOSED:
            _LOGGER.info("Connection closed (By Message Close)")

        elif msg.type == aiohttp.WSMsgType.ERROR:
            _LOGGER.warning(f'Connection error, Description: {self._ws.exception()}')

        else:
            if self._log_events:
                _LOGGER.debug(f'New message received: {str(msg)}')

            self._last_update = datetime.now()

            if msg.data == 'close':
                result = False
            else:
                self.parse_message(msg.data)

                result = True

        return result

    async def close(self):
        _LOGGER.info("Closing connection to WS")

        self._session_id = None

        if self._ws is not None:
            await self._ws.close()

        self._ws = None

        if self._session is not None:
            await self._session.close()

        self._session = None

    def get_subscription_data(self):
        topics_to_subscribe = [{WS_TOPIC_NAME: topic} for topic in self._topics]
        topics_to_unsubscribe = []

        data = {
            WS_TOPIC_SUBSCRIBE: topics_to_subscribe,
            WS_TOPIC_UNSUBSCRIBE: topics_to_unsubscribe,
            WS_SESSION_ID: self._session_id
        }

        subscription_content = json.dumps(data, separators=(STRING_COMMA, STRING_COLON))
        subscription_content_length = len(subscription_content)
        subscription_data = f'{subscription_content_length}\n{subscription_content}'

        _LOGGER.info(f'get_subscription_data - Subscription data: {subscription_data}')

        return subscription_data
