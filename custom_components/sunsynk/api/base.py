"""Abstract base class for Sunsynk API clients."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class SunsynkData:
    """Data model for Sunsynk inverter readings."""

    # Power sensors (W) — None if not yet fetched or invalid
    pv_power: float | None = None
    pv1_power: float | None = None
    pv2_power: float | None = None
    battery_power: float | None = None  # positive = charging, negative = discharging
    grid_power: float | None = None     # positive = import, negative = export
    load_power: float | None = None

    # Battery state
    battery_soc: float | None = None    # percent 0-100
    battery_voltage: float | None = None  # V
    battery_current: float | None = None  # A

    # Grid connection
    grid_connected: bool = False

    # Energy totals (kWh) — today
    pv_energy_today: float | None = None
    battery_charge_today: float | None = None
    battery_discharge_today: float | None = None
    grid_import_today: float | None = None
    grid_export_today: float | None = None
    load_energy_today: float | None = None

    # Energy totals (kWh) — month
    pv_energy_month: float | None = None
    grid_import_month: float | None = None
    load_energy_month: float | None = None

    # Energy totals (kWh) — year
    pv_energy_year: float | None = None
    grid_import_year: float | None = None
    load_energy_year: float | None = None

    # System status
    fault_code: str | None = None
    system_status: str | None = None

    # Weather at plant location
    weather_temperature: float | None = None
    weather_description: str | None = None
    weather_sunrise: str | None = None
    weather_sunset: str | None = None

    # Metadata
    inverter_sn: str = ""
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # Inverter settings (read from /api/v1/common/setting/{sn}/read)
    settings: dict = field(default_factory=dict)


class SunsynkApiClient(ABC):
    """Abstract base class for Sunsynk API clients.

    Both OfficialApiClient and UnofficialApiClient must implement this interface.
    The coordinator uses only this interface — it never knows which implementation is active.
    """

    @abstractmethod
    async def authenticate(self) -> None:
        """Authenticate with the Sunsynk API.

        Raises:
            SunsynkAuthError: If authentication fails (invalid credentials).
            SunsynkCommunicationError: If the API is unreachable.
        """

    @abstractmethod
    async def fetch_all(self) -> SunsynkData:
        """Fetch all inverter data in a single call.

        Returns:
            SunsynkData populated with current inverter readings.

        Raises:
            SunsynkAuthError: If the session has expired (caller should re-authenticate).
            SunsynkCommunicationError: If the API is unreachable.
            SunsynkDataError: If the response contains unexpected data.
        """

    @abstractmethod
    async def write_setting(self, key: str, value: Any) -> None:
        """Write a setting to the inverter.

        Args:
            key: The setting key (e.g. "battery_priority", "grid_charge").
            value: The value to write.

        Raises:
            SunsynkAuthError: If the session has expired.
            SunsynkCommunicationError: If the API is unreachable.
            SunsynkDataError: If the value is rejected by the API.
        """
