"""Event dispatcher for Sunsynk threshold and state change events."""
from __future__ import annotations

from datetime import datetime
import logging

from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

# Event names
EVENT_BATTERY_LOW = "sunsynk_battery_low"
EVENT_SOLAR_LOW = "sunsynk_solar_low"
EVENT_FAULT_DETECTED = "sunsynk_fault_detected"
EVENT_FAULT_CLEARED = "sunsynk_fault_cleared"
EVENT_DAILY_SUMMARY = "sunsynk_daily_summary"
EVENT_SELL_SETTING_CHANGED = "sunsynk_sell_setting_changed"


class SunsynkEventDispatcher:
    """Dispatches HA events based on inverter state changes and threshold crossings.

    Called by the coordinator after each successful data update.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        inverter_sn: str,
        soc_threshold: float,
        solar_threshold: float,
        summary_time: str = "18:00",
    ) -> None:
        """Initialize the event dispatcher."""
        self._hass = hass
        self._inverter_sn = inverter_sn
        self._soc_threshold = soc_threshold
        self._solar_threshold = solar_threshold
        self._summary_time = summary_time
        self._last_summary_date: str | None = None
        self._previous_fault_code: str | None = None

    def update_thresholds(self, soc_threshold: float, solar_threshold: float) -> None:
        """Update configurable thresholds (called when options change)."""
        self._soc_threshold = soc_threshold
        self._solar_threshold = solar_threshold

    def update_summary_time(self, summary_time: str) -> None:
        """Update the daily summary time."""
        self._summary_time = summary_time

    def dispatch(self, data) -> None:
        """Check current data and fire events as appropriate."""
        self._check_battery_soc(data)
        self._check_solar_generation(data)
        self._check_fault_code(data)
        self._check_daily_summary(data)

    def _check_battery_soc(self, data) -> None:
        """Fire sunsynk_battery_low if SOC is below threshold."""
        if data.battery_soc is None:
            return
        if data.battery_soc < self._soc_threshold:
            _LOGGER.debug(
                "Battery SOC %s%% below threshold %s%% — firing event",
                data.battery_soc,
                self._soc_threshold,
            )
            self._hass.bus.async_fire(
                EVENT_BATTERY_LOW,
                {
                    "inverter_sn": self._inverter_sn,
                    "soc": data.battery_soc,
                    "threshold": self._soc_threshold,
                    "timestamp": datetime.now().isoformat(),
                },
            )

    def _check_solar_generation(self, data) -> None:
        """Fire sunsynk_solar_low if PV power is below threshold."""
        if data.pv_power is None:
            return
        if data.pv_power < self._solar_threshold:
            _LOGGER.debug(
                "PV power %sW below threshold %sW — firing event",
                data.pv_power,
                self._solar_threshold,
            )
            self._hass.bus.async_fire(
                EVENT_SOLAR_LOW,
                {
                    "inverter_sn": self._inverter_sn,
                    "pv_power": data.pv_power,
                    "threshold": self._solar_threshold,
                    "timestamp": datetime.now().isoformat(),
                },
            )

    def _check_fault_code(self, data) -> None:
        """Fire fault detected/cleared events on fault code changes."""
        current_fault = data.fault_code or ""
        previous_fault = self._previous_fault_code or ""

        if current_fault and not previous_fault:
            _LOGGER.warning(
                "Fault detected on inverter %s: %s",
                self._inverter_sn,
                current_fault,
            )
            self._hass.bus.async_fire(
                EVENT_FAULT_DETECTED,
                {
                    "inverter_sn": self._inverter_sn,
                    "fault_code": current_fault,
                    "description": current_fault,
                    "timestamp": datetime.now().isoformat(),
                },
            )
        elif not current_fault and previous_fault:
            _LOGGER.info(
                "Fault cleared on inverter %s (was: %s)",
                self._inverter_sn,
                previous_fault,
            )
            self._hass.bus.async_fire(
                EVENT_FAULT_CLEARED,
                {
                    "inverter_sn": self._inverter_sn,
                    "previous_fault_code": previous_fault,
                    "timestamp": datetime.now().isoformat(),
                },
            )

        self._previous_fault_code = current_fault or None

    def _check_daily_summary(self, data) -> None:
        """Fire daily summary event once per day at configured time."""
        now = datetime.now()
        today = now.strftime("%Y-%m-%d")
        current_time = now.strftime("%H:%M")

        # Only fire if we haven't fired today AND current time >= summary time
        if self._last_summary_date == today:
            return
        if current_time < self._summary_time:
            return

        self._last_summary_date = today
        self._hass.bus.async_fire(
            EVENT_DAILY_SUMMARY,
            {
                "inverter_sn": self._inverter_sn,
                "date": today,
                "pv_energy_today": data.pv_energy_today,
                "grid_import_today": data.grid_import_today,
                "grid_export_today": data.grid_export_today,
                "load_energy_today": data.load_energy_today,
                "battery_charge_today": data.battery_charge_today,
                "battery_discharge_today": data.battery_discharge_today,
                "timestamp": now.isoformat(),
            },
        )
        _LOGGER.info(
            "Daily energy summary fired for inverter %s (date: %s)",
            self._inverter_sn,
            today,
        )
