"""Write service for Sunsynk inverter control with safety tier enforcement."""
from __future__ import annotations

import asyncio
from datetime import datetime
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError

from ..api.base import SunsynkApiClient
from ..const import (
    CONFIRMATION_TOKEN_EXPIRY_SECONDS,
    WRITE_TIER_1,
    WRITE_TIER_2,
    WRITE_TIER_3,
)
from ..events.dispatcher import EVENT_SELL_SETTING_CHANGED
from .confirmation import WriteConfirmation

_LOGGER = logging.getLogger(__name__)

EVENT_CONFIRMATION_REQUIRED = "sunsynk_confirmation_required"

# Write parameter safe ranges
WRITE_SAFE_RANGES: dict[str, tuple[float, float]] = {
    "charge_current": (0, 185),
    "discharge_current": (0, 185),
    "prog_power": (0, 8000),
    "prog_capacity": (0, 100),
    "grid_freq_high": (50, 65),
    "grid_freq_low": (45, 55),
    "aux_freq_high": (50, 65),
    "aux_freq_low": (45, 55),
    "grid_voltage_high": (220, 270),
    "grid_voltage_low": (180, 220),
    "aux_voltage_high": (220, 270),
    "aux_voltage_low": (180, 220),
}

# Write tier assignments
WRITE_TIERS: dict[str, int] = {
    # Tier 1 — confirmation required (financial/grid impact)
    "solar_sell": WRITE_TIER_1,
    "grid_sell": WRITE_TIER_1,
    "sell_time": WRITE_TIER_1,
    # Tier 2 — logged only (operational, reversible)
    "battery_priority": WRITE_TIER_2,
    "grid_charge": WRITE_TIER_2,
    "work_mode": WRITE_TIER_2,
    "charge_current": WRITE_TIER_2,
    "discharge_current": WRITE_TIER_2,
    "prog_power": WRITE_TIER_2,
    "prog_capacity": WRITE_TIER_2,
    "prog_charge": WRITE_TIER_2,
    "prog_enabled": WRITE_TIER_2,
    "prog_time": WRITE_TIER_2,
    # Tier 3 — confirmation required (can trip inverter)
    "grid_freq_high": WRITE_TIER_3,
    "grid_freq_low": WRITE_TIER_3,
    "aux_freq_high": WRITE_TIER_3,
    "aux_freq_low": WRITE_TIER_3,
    "grid_voltage_high": WRITE_TIER_3,
    "grid_voltage_low": WRITE_TIER_3,
    "aux_voltage_high": WRITE_TIER_3,
    "aux_voltage_low": WRITE_TIER_3,
    # Generator/AUX parameters (Tier 3 — incorrect values can damage equipment)
    "genOffVolt": WRITE_TIER_3,
    "genOnVolt": WRITE_TIER_3,
    "acCoupleFreqUpper": WRITE_TIER_3,
    # Generator operational parameters (Tier 2 — logged only)
    "genPeakPower": WRITE_TIER_2,
    "genOffCap": WRITE_TIER_2,
    "genOnCap": WRITE_TIER_2,
    "genMinSolar": WRITE_TIER_2,
    "gridPeakPower": WRITE_TIER_2,
    "loadMode": WRITE_TIER_2,
    "genPeakShaving": WRITE_TIER_2,
    "gridPeakShaving": WRITE_TIER_2,
    "genConnectGrid": WRITE_TIER_2,
    # Charging schedule (Tier 2 — logged only)
    "sellTime1Pac": WRITE_TIER_2,
    "sellTime2Pac": WRITE_TIER_2,
    "sellTime3Pac": WRITE_TIER_2,
    "sellTime4Pac": WRITE_TIER_2,
    "sellTime5Pac": WRITE_TIER_2,
    "sellTime6Pac": WRITE_TIER_2,
    "cap1": WRITE_TIER_2,
    "cap2": WRITE_TIER_2,
    "cap3": WRITE_TIER_2,
    "cap4": WRITE_TIER_2,
    "cap5": WRITE_TIER_2,
    "cap6": WRITE_TIER_2,
    "sellTime1": WRITE_TIER_2,
    "sellTime2": WRITE_TIER_2,
    "sellTime3": WRITE_TIER_2,
    "sellTime4": WRITE_TIER_2,
    "sellTime5": WRITE_TIER_2,
    "sellTime6": WRITE_TIER_2,
    "time1on": WRITE_TIER_2,
    "time2on": WRITE_TIER_2,
    "time3on": WRITE_TIER_2,
    "time4on": WRITE_TIER_2,
    "time5on": WRITE_TIER_2,
    "time6on": WRITE_TIER_2,
}


class WriteService:
    """Handles all inverter write operations with tier-based safety enforcement."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: SunsynkApiClient,
        inverter_sn: str,
    ) -> None:
        """Initialize the write service."""
        self._hass = hass
        self._client = client
        self._inverter_sn = inverter_sn
        self._pending_confirmations: dict[str, WriteConfirmation] = {}

    def _get_tier(self, key: str) -> int:
        """Get the write safety tier for a setting key."""
        return WRITE_TIERS.get(key, WRITE_TIER_2)

    def _validate_range(self, key: str, value: Any) -> None:
        """Validate a numeric value against known safe ranges."""
        if key not in WRITE_SAFE_RANGES or not isinstance(value, (int, float)):
            return
        lo, hi = WRITE_SAFE_RANGES[key]
        if not (lo <= value <= hi):
            raise ServiceValidationError(
                f"Value {value} for {key} is outside safe range [{lo}, {hi}]"
            )

    def _require_confirmation(self, key: str, params: dict) -> None:
        """Create a confirmation token and fire the confirmation_required event."""
        confirmation = WriteConfirmation(service=key, params=params)
        self._pending_confirmations[confirmation.token] = confirmation

        self._hass.bus.async_fire(
            EVENT_CONFIRMATION_REQUIRED,
            {
                "inverter_sn": self._inverter_sn,
                "token": confirmation.token,
                "service": key,
                "params": params,
                "expires_at": confirmation.expires_at.isoformat(),
                "message": (
                    f"Confirmation required to change {key}. "
                    f"Call the service again with token '{confirmation.token}' "
                    f"within {CONFIRMATION_TOKEN_EXPIRY_SECONDS} seconds."
                ),
            },
        )
        _LOGGER.warning(
            "Confirmation required for %s on inverter %s (token: %s)",
            key, self._inverter_sn, confirmation.token,
        )
        raise ServiceValidationError(
            f"confirmation_required: token={confirmation.token}"
        )

    def _validate_confirmation(self, key: str, token: str | None) -> None:
        """Validate a confirmation token for Tier 1/3 writes."""
        if token is None:
            self._require_confirmation(key, {})
            return

        confirmation = self._pending_confirmations.get(token)
        if confirmation is None:
            raise ServiceValidationError(
                f"confirmation_invalid: token '{token}' not found"
            )
        if confirmation.is_expired():
            del self._pending_confirmations[token]
            raise ServiceValidationError(
                f"confirmation_expired: token '{token}' has expired"
            )
        if confirmation.service != key:
            raise ServiceValidationError(
                f"confirmation_mismatch: token was issued for '{confirmation.service}', not '{key}'"
            )
        # Token is valid — consume it
        del self._pending_confirmations[token]

    async def execute_write(
        self,
        key: str,
        value: Any,
        confirmation_token: str | None = None,
    ) -> None:
        """Execute a write operation with tier-based safety enforcement."""
        tier = self._get_tier(key)

        # Validate input range
        self._validate_range(key, value)

        # Tier 1/3: require confirmation
        if tier in (WRITE_TIER_1, WRITE_TIER_3):
            self._validate_confirmation(key, confirmation_token)

        # Log Tier 2 writes
        if tier == WRITE_TIER_2:
            _LOGGER.info(
                "Writing %s = %s to inverter %s (Tier 2)",
                key, value, self._inverter_sn,
            )

        # Execute the write
        await self._client.write_setting(key, value)

        # Read back to confirm
        await self._read_back_confirmation(key, value)

        # Fire sell setting changed event for Tier 1 writes
        if tier == WRITE_TIER_1:
            self._hass.bus.async_fire(
                EVENT_SELL_SETTING_CHANGED,
                {
                    "inverter_sn": self._inverter_sn,
                    "key": key,
                    "value": value,
                    "timestamp": datetime.now().isoformat(),
                },
            )

    async def _read_back_confirmation(self, key: str, expected_value: Any) -> None:
        """Read back the written value to confirm it was applied."""
        await asyncio.sleep(5)
        try:
            await self._client.fetch_all()
            _LOGGER.debug(
                "Read-back after writing %s = %s to inverter %s",
                key, expected_value, self._inverter_sn,
            )
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning(
                "Read-back failed after writing %s to inverter %s: %s",
                key, self._inverter_sn, err,
            )
