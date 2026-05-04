"""Config flow for Sunsynk Solar Inverter."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import (
    API_MODE_OFFICIAL,
    API_MODE_UNOFFICIAL,
    DEFAULT_POLL_INTERVAL,
    DEFAULT_RETENTION_DAYS,
    DEFAULT_SOC_THRESHOLD,
    DEFAULT_SOLAR_THRESHOLD,
    DEFAULT_SUMMARY_TIME,
    DOMAIN,
    MAX_POLL_INTERVAL,
    MIN_POLL_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

STEP_API_MODE = "api_mode"
STEP_OFFICIAL_CREDS = "official_creds"
STEP_UNOFFICIAL_CREDS = "unofficial_creds"
STEP_SSL_WARNING = "ssl_warning"
STEP_INVERTER = "inverter"

SCHEMA_API_MODE = vol.Schema({
    vol.Required("api_mode", default=API_MODE_UNOFFICIAL): vol.In(
        [API_MODE_UNOFFICIAL, API_MODE_OFFICIAL]
    ),
})

SCHEMA_OFFICIAL_CREDS = vol.Schema({
    vol.Required("app_key"): str,
    vol.Required("app_secret"): str,
})

SCHEMA_UNOFFICIAL_CREDS = vol.Schema({
    vol.Required("username"): str,
    vol.Required("password"): str,
    vol.Optional("region", default="api.sunsynk.net"): vol.In(
        ["api.sunsynk.net", "pv.inteless.com"]
    ),
})

SCHEMA_INVERTER = vol.Schema({
    vol.Required("inverter_sn"): str,
})

SCHEMA_OPTIONS = vol.Schema({
    vol.Optional("poll_interval_minutes", default=5): vol.All(
        int, vol.Range(min=5, max=60)
    ),
    vol.Optional("soc_threshold", default=DEFAULT_SOC_THRESHOLD): vol.All(
        float, vol.Range(min=0, max=100)
    ),
    vol.Optional("solar_threshold", default=DEFAULT_SOLAR_THRESHOLD): vol.All(
        float, vol.Range(min=0, max=20000)
    ),
    vol.Optional("summary_time", default=DEFAULT_SUMMARY_TIME): str,
    vol.Optional("retention_days", default=DEFAULT_RETENTION_DAYS): vol.All(
        int, vol.Range(min=1, max=365)
    ),
})


class SunsynkConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Sunsynk Solar Inverter."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._data: dict[str, Any] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step 1: Choose API mode — default to Official API."""
        if user_input is not None:
            self._data["api_mode"] = user_input["api_mode"]
            if user_input["api_mode"] == API_MODE_OFFICIAL:
                return await self.async_step_ssl_warning()
            return await self.async_step_unofficial_creds()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("api_mode", default=API_MODE_OFFICIAL): vol.In(
                    [API_MODE_OFFICIAL, API_MODE_UNOFFICIAL]
                ),
            }),
            description_placeholders={
                "official": "Official API (appKey + appSecret) — recommended",
                "unofficial": "Unofficial API (username + password) — may be blocked by Cloudflare",
            },
        )

    async def async_step_ssl_warning(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step 2a: SSL warning for Official API."""
        if user_input is not None:
            if user_input.get("acknowledged"):
                return await self.async_step_official_creds()
            # User did not acknowledge — go back
            return await self.async_step_user()

        return self.async_show_form(
            step_id="ssl_warning",
            data_schema=vol.Schema({
                vol.Required("acknowledged", default=False): bool,
            }),
            description_placeholders={
                "warning": (
                    "⚠️ SECURITY WARNING: The official Sunsynk API requires SSL "
                    "verification to be disabled. This means your API credentials "
                    "could be intercepted on untrusted networks. Only use this on "
                    "a trusted home network. Check the box below to acknowledge."
                )
            },
        )

    async def async_step_official_creds(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step 2b: Official API credentials."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_inverter()

        return self.async_show_form(
            step_id="official_creds",
            data_schema=SCHEMA_OFFICIAL_CREDS,
            errors=errors,
        )

    async def async_step_unofficial_creds(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step 2c: Unofficial API credentials."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_inverter()

        return self.async_show_form(
            step_id="unofficial_creds",
            data_schema=SCHEMA_UNOFFICIAL_CREDS,
            errors=errors,
        )

    async def async_step_inverter(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step 3: Inverter serial number and region."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._data.update(user_input)

            # Validate credentials against the API
            try:
                await self._validate_credentials()
            except Exception as err:  # noqa: BLE001
                _LOGGER.error("Credential validation failed: %s", err)
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(self._data["inverter_sn"])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"Sunsynk {self._data['inverter_sn']}",
                    data=self._data,
                )

        return self.async_show_form(
            step_id="inverter",
            data_schema=SCHEMA_INVERTER,
            errors=errors,
        )

    async def _validate_credentials(self) -> None:
        """Validate credentials by attempting authentication."""
        api_mode = self._data.get("api_mode", API_MODE_UNOFFICIAL)

        if api_mode == API_MODE_OFFICIAL:
            from .api.official import OfficialApiClient
            client = OfficialApiClient(
                app_key=self._data["app_key"],
                app_secret=self._data["app_secret"],
                inverter_sn=self._data.get("inverter_sn", ""),
            )
        else:
            from .api.unofficial import UnofficialApiClient
            client = UnofficialApiClient(
                username=self._data["username"],
                password=self._data["password"],
                inverter_sn=self._data.get("inverter_sn", ""),
                region=self._data.get("region", "api.sunsynk.net"),
            )

        await client.authenticate()

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> SunsynkOptionsFlow:
        """Return the options flow."""
        return SunsynkOptionsFlow(config_entry)


class SunsynkOptionsFlow(config_entries.OptionsFlow):
    """Handle options for Sunsynk integration."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = self.config_entry.options
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional(
                    "poll_interval_minutes",
                    default=current.get("poll_interval_minutes", 5),
                ): vol.All(int, vol.Range(min=5, max=60)),
                vol.Optional(
                    "soc_threshold",
                    default=current.get("soc_threshold", DEFAULT_SOC_THRESHOLD),
                ): vol.All(float, vol.Range(min=0, max=100)),
                vol.Optional(
                    "solar_threshold",
                    default=current.get("solar_threshold", DEFAULT_SOLAR_THRESHOLD),
                ): vol.All(float, vol.Range(min=0, max=20000)),
                vol.Optional(
                    "summary_time",
                    default=current.get("summary_time", DEFAULT_SUMMARY_TIME),
                ): str,
                vol.Optional(
                    "retention_days",
                    default=current.get("retention_days", DEFAULT_RETENTION_DAYS),
                ): vol.All(int, vol.Range(min=1, max=365)),
            }),
        )
