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
    DEFAULT_RETENTION_DAYS,
    DEFAULT_SOC_THRESHOLD,
    DEFAULT_SOLAR_THRESHOLD,
    DEFAULT_SUMMARY_TIME,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

SCHEMA_INVERTER = vol.Schema({
    vol.Required("inverter_sn"): str,
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
        """Step 1: Choose API mode."""
        if user_input is not None:
            self._data["api_mode"] = user_input["api_mode"]
            if user_input["api_mode"] == API_MODE_OFFICIAL:
                return await self.async_step_official_creds()
            return await self.async_step_unofficial_creds()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("api_mode", default=API_MODE_OFFICIAL): vol.In(
                    [API_MODE_OFFICIAL, API_MODE_UNOFFICIAL]
                ),
            }),
        )

    async def async_step_official_creds(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step 2a: Official API credentials (appKey + appSecret + account)."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_inverter()

        return self.async_show_form(
            step_id="official_creds",
            data_schema=vol.Schema({
                vol.Required("app_key"): str,
                vol.Required("app_secret"): str,
                vol.Required("username"): str,
                vol.Required("password"): str,
            }),
            errors=errors,
        )

    async def async_step_unofficial_creds(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step 2b: Unofficial API credentials (username + password).

        Note: May not work on newer accounts due to Cloudflare bot protection.
        """
        errors: dict[str, str] = {}

        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_inverter()

        return self.async_show_form(
            step_id="unofficial_creds",
            data_schema=vol.Schema({
                vol.Required("username"): str,
                vol.Required("password"): str,
                vol.Optional("region", default="api.sunsynk.net"): vol.In(
                    ["api.sunsynk.net", "pv.inteless.com"]
                ),
            }),
            errors=errors,
        )

    async def async_step_inverter(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step 3: Inverter serial number."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._data.update(user_input)
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
                username=self._data.get("username", ""),
                password=self._data.get("password", ""),
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

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle reconfiguration (e.g. password change)."""
        errors: dict[str, str] = {}
        entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        assert entry is not None

        if user_input is not None:
            # Merge new credentials with existing data
            updated_data = {**entry.data, **user_input}
            self._data = updated_data
            try:
                await self._validate_credentials()
            except Exception as err:  # noqa: BLE001
                _LOGGER.error("Reconfigure validation failed: %s", err)
                errors["base"] = "cannot_connect"
            else:
                self.hass.config_entries.async_update_entry(entry, data=updated_data)
                await self.hass.config_entries.async_reload(entry.entry_id)
                return self.async_abort(reason="reconfigure_successful")

        # Show form with current values (password blank for security)
        api_mode = entry.data.get("api_mode", API_MODE_UNOFFICIAL)

        if api_mode == API_MODE_OFFICIAL:
            schema = vol.Schema({
                vol.Required("username", default=entry.data.get("username", "")): str,
                vol.Required("password"): str,
                vol.Required("app_key", default=entry.data.get("app_key", "")): str,
                vol.Required("app_secret"): str,
            })
        else:
            schema = vol.Schema({
                vol.Required("username", default=entry.data.get("username", "")): str,
                vol.Required("password"): str,
            })

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=schema,
            errors=errors,
        )

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
                ): vol.All(int, vol.Range(min=1, max=60)),
                vol.Optional(
                    "pv_strings",
                    default=current.get("pv_strings", 2),
                ): vol.All(int, vol.Range(min=1, max=4)),
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
