import logging
from typing import Optional

from cryptography.fernet import InvalidToken

from homeassistant.config_entries import ConfigEntry

from .. import get_ha
from ..clients import LoginException
from ..clients.web_api import EdgeOSWebAPI
from ..helpers.const import *
from ..managers.configuration_manager import ConfigManager
from ..managers.password_manager import PasswordManager
from ..models import AlreadyExistsError, LoginError
from ..models.config_data import ConfigData

_LOGGER = logging.getLogger(__name__)


class ConfigFlowManager:
    _config_manager: ConfigManager
    _password_manager: PasswordManager
    _options: Optional[dict]
    _data: Optional[dict]
    _config_entry: Optional[ConfigEntry]

    def __init__(self):
        self._config_entry = None

        self._options = None
        self._data = None

        self._is_initialized = True
        self._hass = None

        self._available_actions = {
            CONF_STORE_DEBUG_FILE: self._execute_store_debug_file
        }

    async def initialize(self, hass, config_entry: Optional[ConfigEntry] = None):
        self._config_entry = config_entry
        self._hass = hass

        self._password_manager = PasswordManager(self._hass)
        self._config_manager = ConfigManager(self._password_manager)

        data = {}
        options = {}

        if self._config_entry is not None:
            data = self._config_entry.data
            options = self._config_entry.options

        await self.update_data(data, CONFIG_FLOW_INIT)
        await self.update_options(options, CONFIG_FLOW_INIT)

    @property
    def config_data(self) -> ConfigData:
        return self._config_manager.data

    @property
    def title(self) -> str:
        return self._data.get(ENTRY_PRIMARY_KEY)

    async def update_options(self, options: dict, flow: str):
        _LOGGER.debug("Update options")

        validate_login = False
        actions = []

        new_options = await self._clone_items(options, flow)

        if flow == CONFIG_FLOW_OPTIONS:
            self._validate_unique_name(new_options)

            validate_login = self._should_validate_login(new_options)

            self._move_option_to_data(new_options)

            actions = self._get_actions(new_options)

        self._options = new_options

        await self._update_entry()

        if validate_login:
            await self._handle_data(flow)

        for action in actions:
            action()

        return new_options

    async def update_data(self, data: dict, flow: str):
        _LOGGER.debug("Update data")

        if flow == CONFIG_FLOW_DATA:
            self._validate_unique_name(data)

        self._data = await self._clone_items(data, flow)

        await self._update_entry()

        await self._handle_data(flow)

    def get_data_user_input(self):
        data = self.clone_items(self._data)
        title = ""

        if ENTRY_PRIMARY_KEY in data:
            title = data[ENTRY_PRIMARY_KEY]

            del data[ENTRY_PRIMARY_KEY]

        return title, data

    def get_options_user_input(self):
        data = self.clone_items(self._options)
        title = ""

        if ENTRY_PRIMARY_KEY in data:
            title = data[ENTRY_PRIMARY_KEY]
            del data[ENTRY_PRIMARY_KEY]

        return title, data

    def _validate_unique_name(self, user_input):
        entry_primary_key = user_input.get(ENTRY_PRIMARY_KEY, "")

        if self.title is None or self.title != entry_primary_key:
            ha = get_ha(self._hass, entry_primary_key)

            if ha is not None:
                raise AlreadyExistsError(entry_primary_key)

    def _get_default_fields(self, flow, config_data: Optional[ConfigData] = None):
        if config_data is None:
            config_data = self.config_data

        fields = {}

        if flow == CONFIG_FLOW_DATA:
            fields[vol.Optional(CONF_NAME, default=config_data.name)] = str

        fields[vol.Optional(CONF_HOST, default=config_data.host)] = str
        fields[vol.Optional(CONF_USERNAME, default=config_data.username)] = str
        fields[
            vol.Optional(CONF_PASSWORD, default=config_data.password_clear_text)
        ] = str
        fields[vol.Optional(CONF_UNIT, default=config_data.unit)] = vol.In(
            ALLOWED_UNITS_LIST
        )

        return fields

    async def get_default_data(self, user_input):
        config_data = await self._config_manager.get_basic_data(user_input)

        fields = self._get_default_fields(CONFIG_FLOW_DATA, config_data)

        data_schema = vol.Schema(fields)

        return data_schema

    def get_default_options(self):
        system_data = {}
        config_data = self.config_data
        ha = self._get_ha(self._config_entry.entry_id)

        if ha is not None:
            system_data = ha.data_manager.system_data

        all_interfaces = self._get_available_options(system_data, INTERFACES_KEY)
        all_devices = self._get_available_options(system_data, STATIC_DEVICES_KEY)

        monitored_devices = self._get_options(config_data.monitored_devices)
        monitored_interfaces = self._get_options(config_data.monitored_interfaces)
        device_trackers = self._get_options(config_data.device_trackers)

        fields = self._get_default_fields(CONFIG_FLOW_OPTIONS)

        fields[vol.Optional(CONF_CLEAR_CREDENTIALS, default=False)] = bool
        fields[
            vol.Optional(
                CONF_CONSIDER_AWAY_INTERVAL, default=config_data.consider_away_interval
            )
        ] = int
        fields[vol.Optional(CONF_UNIT, default=config_data.unit)] = vol.In(
            ALLOWED_UNITS_LIST
        )
        fields[
            vol.Optional(CONF_MONITORED_DEVICES, default=monitored_devices)
        ] = cv.multi_select(all_devices)
        fields[
            vol.Optional(CONF_MONITORED_INTERFACES, default=monitored_interfaces)
        ] = cv.multi_select(all_interfaces)
        fields[
            vol.Optional(CONF_TRACK_DEVICES, default=device_trackers)
        ] = cv.multi_select(all_devices)
        fields[
            vol.Optional(
                CONF_UPDATE_ENTITIES_INTERVAL,
                default=config_data.update_entities_interval,
            )
        ] = cv.positive_int

        fields[
            vol.Optional(
                CONF_UPDATE_API_INTERVAL, default=config_data.update_api_interval
            )
        ] = cv.positive_int

        fields[vol.Optional(CONF_STORE_DEBUG_FILE, default=False)] = bool
        fields[vol.Optional(CONF_LOG_LEVEL, default=config_data.log_level)] = vol.In(
            LOG_LEVELS
        )
        fields[
            vol.Optional(
                CONF_LOG_INCOMING_MESSAGES, default=config_data.log_incoming_messages
            )
        ] = bool

        data_schema = vol.Schema(fields)

        return data_schema

    async def _update_entry(self):
        try:
            entry = ConfigEntry(
                0, "", "", self._data, "", "", {}, options=self._options
            )

            await self._config_manager.update(entry)
        except InvalidToken:
            _LOGGER.info("Reset password")

            del self._data[CONF_PASSWORD]

            entry = ConfigEntry(
                0, "", "", self._data, "", "", {}, options=self._options
            )

            await self._config_manager.update(entry)

    async def _handle_password(self, user_input):
        if CONF_CLEAR_CREDENTIALS in user_input:
            clear_credentials = user_input.get(CONF_CLEAR_CREDENTIALS)

            if clear_credentials:
                del user_input[CONF_USERNAME]
                del user_input[CONF_PASSWORD]
            del user_input[CONF_CLEAR_CREDENTIALS]

        if CONF_PASSWORD in user_input:
            password_clear_text = user_input[CONF_PASSWORD]
            password = await self._password_manager.encrypt(password_clear_text)

            user_input[CONF_PASSWORD] = password

    @staticmethod
    def _get_user_input_option(options, key):
        result = options.get(key, [])

        return result

    async def _clone_items(self, user_input, flow: str):
        new_user_input = {}

        if user_input is not None:
            for key in user_input:
                user_input_data = user_input[key]

                new_user_input[key] = user_input_data

            if flow != CONFIG_FLOW_INIT:
                await self._handle_password(new_user_input)

        return new_user_input

    @staticmethod
    def clone_items(user_input):
        new_user_input = {}

        if user_input is not None:
            for key in user_input:
                user_input_data = user_input[key]

                new_user_input[key] = user_input_data

        return new_user_input

    def _should_validate_login(self, user_input: dict):
        validate_login = False
        data = self._data

        for conf in CONF_ARR:
            if data.get(conf) != user_input.get(conf):
                validate_login = True

                break

        return validate_login

    def _get_actions(self, options):
        actions = []

        for action in self._available_actions:
            if action in options:
                if options.get(action, False):
                    execute_action = self._available_actions[action]

                    actions.append(execute_action)

            del options[action]

        return actions

    def _execute_store_debug_file(self):
        ha = self._get_ha()

        if ha is not None:
            ha.service_save_debug_data()

    def _get_ha(self, key: str = None):
        if key is None:
            key = self.title

        ha = get_ha(self._hass, key)

        return ha

    def _move_option_to_data(self, options):
        for conf in CONF_ARR:
            if conf in options:
                self._data[conf] = options[conf]

                del options[conf]

    async def _handle_data(self, flow):
        if flow != CONFIG_FLOW_INIT:
            await self._valid_login()

        if flow == CONFIG_FLOW_OPTIONS:
            config_entries = self._hass.config_entries
            config_entries.async_update_entry(self._config_entry, data=self._data)

    @staticmethod
    def _get_options(data):
        result = []

        if data is not None:
            if isinstance(data, list):
                result = data
            else:
                clean_data = data.replace(" ", "")
                result = clean_data.split(",")

        return result

    @staticmethod
    def _get_available_options(system_data, key):
        all_items = system_data.get(key, {})

        available_items = {}

        for item_key in all_items:
            item = all_items[item_key]
            item_name = item.get(CONF_NAME)

            available_items[item_key] = item_name

        return available_items

    async def _valid_login(self):
        errors = None

        name = f"{DEFAULT_NAME} {self.title}"

        try:
            api = EdgeOSWebAPI(self._hass, self._config_manager)

            await api.initialize()

            if await api.login(throw_exception=True):
                await api.async_send_heartbeat()

                if not api.is_connected:
                    _LOGGER.warning(
                        f"Failed to login {name} due to invalid credentials"
                    )
                    errors = {"base": "invalid_credentials"}

                device_data = await api.get_devices_data()

                if device_data is None:
                    _LOGGER.warning(f"Failed to retrieve {name} device data")
                    errors = {"base": "empty_device_data"}
                else:
                    system_data = device_data.get("system", {})
                    traffic_analysis_data = system_data.get("traffic-analysis", {})
                    dpi = traffic_analysis_data.get("dpi", "disable")
                    export = traffic_analysis_data.get("export", "disable")

                    error_prefix = f"Invalid {name} configuration -"

                    if dpi != "enable":
                        _LOGGER.warning(
                            f"{error_prefix} Deep Packet Inspection (DPI) is disabled"
                        )
                        errors = {"base": "invalid_dpi_configuration"}

                    if export != "enable":
                        _LOGGER.warning(
                            f"{error_prefix} Traffic Analysis Export is disabled"
                        )
                        errors = {"base": "invalid_export_configuration"}

            else:
                _LOGGER.warning(f"Failed to login {name}")

                errors = {"base": "auth_general_error"}

        except LoginException as ex:
            _LOGGER.warning(
                f"Failed to login {name} due to HTTP Status Code: {ex.status_code}"
            )

            errors = {"base": HTTP_ERRORS.get(ex.status_code, "auth_general_error")}

        except Exception as ex:
            _LOGGER.warning(f"Failed to login {name} due to general error: {str(ex)}")

            errors = {"base": "auth_general_error"}

        if errors is not None:
            raise LoginError(errors)
