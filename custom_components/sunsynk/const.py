"""Constants for the Sunsynk Solar Inverter integration."""
from __future__ import annotations

from datetime import timedelta

DOMAIN = "sunsynk"

# Polling configuration
DEFAULT_POLL_INTERVAL = timedelta(minutes=5)
MIN_POLL_INTERVAL = timedelta(minutes=5)
MAX_POLL_INTERVAL = timedelta(minutes=60)

# Alert thresholds
DEFAULT_SOC_THRESHOLD = 20.0       # percent
DEFAULT_SOLAR_THRESHOLD = 500.0    # watts
DEFAULT_SUMMARY_TIME = "18:00"

# API modes
API_MODE_OFFICIAL = "official"
API_MODE_UNOFFICIAL = "unofficial"

# Write safety tiers
WRITE_TIER_1 = 1   # Confirmation required (sell settings, financial impact)
WRITE_TIER_2 = 2   # Logged only (battery mode, priority, schedule)
WRITE_TIER_3 = 3   # Confirmation required (Hz/voltage — can trip inverter)

# Confirmation token
CONFIRMATION_TOKEN_EXPIRY_SECONDS = 60

# Data retention
DEFAULT_RETENTION_DAYS = 30

# Valid ranges for sensor data validation (bad data rejection)
SENSOR_VALID_RANGES: dict[str, tuple[float, float]] = {
    # Power sensors (W)
    "pv_power": (0, 20000),
    "battery_power": (-20000, 20000),
    "battery_soc": (0, 100),
    "grid_power": (-20000, 20000),
    "load_power": (0, 20000),
    # Energy sensors (kWh) — daily totals shouldn't exceed 200 kWh
    "pv_energy_today": (0, 200),
    "battery_charge_today": (0, 200),
    "battery_discharge_today": (0, 200),
    "grid_import_today": (0, 200),
    "grid_export_today": (0, 200),
    "load_energy_today": (0, 200),
    # Monthly/yearly — higher bounds
    "pv_energy_month": (0, 5000),
    "grid_import_month": (0, 5000),
    "load_energy_month": (0, 5000),
    "pv_energy_year": (0, 60000),
    "grid_import_year": (0, 60000),
    "load_energy_year": (0, 60000),
}
