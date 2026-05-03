"""SQLite time-series storage for Sunsynk inverter readings."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from pathlib import Path

import aiosqlite

from ..api.base import SunsynkData

_LOGGER = logging.getLogger(__name__)

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS inverter_readings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    inverter_sn TEXT NOT NULL,
    timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    sensor_key TEXT NOT NULL,
    value REAL
);
CREATE INDEX IF NOT EXISTS idx_readings_lookup
    ON inverter_readings (inverter_sn, sensor_key, timestamp);
"""

INSERT_SQL = """
INSERT INTO inverter_readings (inverter_sn, timestamp, sensor_key, value)
VALUES (?, ?, ?, ?)
"""

DELETE_OLD_SQL = """
DELETE FROM inverter_readings
WHERE timestamp < ?
"""

# Sensor fields to persist from SunsynkData
PERSISTED_SENSORS = [
    "pv_power",
    "battery_power",
    "battery_soc",
    "grid_power",
    "load_power",
    "pv_energy_today",
    "grid_import_today",
    "grid_export_today",
    "load_energy_today",
    "battery_charge_today",
    "battery_discharge_today",
]


class SunsynkStorage:
    """Async SQLite storage for Sunsynk time-series readings.

    Stores sensor readings with a configurable rolling retention window.
    All operations are async (aiosqlite) and never block the event loop.
    """

    def __init__(self, db_path: str, retention_days: int = 30) -> None:
        """Initialize the storage."""
        self._db_path = db_path
        self._retention_days = retention_days
        self._db: aiosqlite.Connection | None = None

    async def async_init(self) -> None:
        """Initialize the database and create tables."""
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        self._db = await aiosqlite.connect(self._db_path)
        await self._db.executescript(CREATE_TABLE_SQL)
        await self._db.commit()
        _LOGGER.debug("Sunsynk storage initialized at %s", self._db_path)

    async def async_store(self, data: SunsynkData) -> None:
        """Store a SunsynkData reading to the database.

        Also purges readings older than the retention window.
        """
        if self._db is None:
            return

        now = datetime.now()
        inverter_sn = data.inverter_sn

        # Insert readings for all persisted sensors
        rows = []
        for key in PERSISTED_SENSORS:
            value = getattr(data, key, None)
            if value is not None:
                rows.append((inverter_sn, now.isoformat(), key, float(value)))

        if rows:
            await self._db.executemany(INSERT_SQL, rows)

        # Purge old readings
        cutoff = (now - timedelta(days=self._retention_days)).isoformat()
        await self._db.execute(DELETE_OLD_SQL, (cutoff,))

        await self._db.commit()

    async def async_close(self) -> None:
        """Close the database connection."""
        if self._db is not None:
            await self._db.close()
            self._db = None
