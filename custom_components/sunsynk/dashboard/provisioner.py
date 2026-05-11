"""Idempotent Lovelace dashboard provisioner for Sunsynk."""
from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.core import HomeAssistant
from homeassistant.helpers import json as json_helper

from .layout import get_dashboard_config

_LOGGER = logging.getLogger(__name__)

DASHBOARD_URL_PATH = "sunsynk"
DASHBOARD_TITLE = "Sunsynk Solar"
DASHBOARD_FILENAME = ".storage/lovelace.sunsynk"


async def async_provision_dashboard(
    hass: HomeAssistant,
    inverter_sn: str,
) -> None:
    """Create the Sunsynk Lovelace dashboard if it doesn't already exist.

    This writes a storage-mode dashboard config file directly, which is the
    most reliable approach across HA versions. The dashboard appears in the
    sidebar after a restart or lovelace reload.
    """
    try:
        # Check if dashboard storage file already exists
        storage_path = Path(hass.config.path(DASHBOARD_FILENAME))
        if storage_path.exists():
            _LOGGER.debug(
                "Sunsynk dashboard storage already exists, skipping provisioning"
            )
            return

        # Try the programmatic approach first (HA 2024.1+)
        if await _try_programmatic_provision(hass, inverter_sn):
            return

        # Fallback: write the storage file directly
        await _write_dashboard_storage(hass, inverter_sn)

    except Exception as err:  # noqa: BLE001
        _LOGGER.warning(
            "Failed to provision Sunsynk dashboard: %s. "
            "You can create it manually in the HA UI.",
            err,
        )


async def _try_programmatic_provision(
    hass: HomeAssistant, inverter_sn: str
) -> bool:
    """Try to create dashboard via HA's lovelace API."""
    try:
        lovelace = hass.data.get("lovelace")
        if lovelace is None:
            return False

        dashboards_collection = getattr(lovelace, "dashboards", None)
        if dashboards_collection is None:
            return False

        # Check if already exists
        for dashboard in dashboards_collection.async_items():
            if dashboard.get("url_path") == DASHBOARD_URL_PATH:
                _LOGGER.debug("Sunsynk dashboard already registered")
                return True

        # Create the dashboard entry
        await dashboards_collection.async_create_item({
            "url_path": DASHBOARD_URL_PATH,
            "title": DASHBOARD_TITLE,
            "icon": "mdi:solar-power",
            "show_in_sidebar": True,
            "require_admin": False,
            "mode": "storage",
        })

        # Now write the view config
        await _write_dashboard_storage(hass, inverter_sn)
        _LOGGER.info("Sunsynk dashboard provisioned via API")
        return True

    except Exception as err:  # noqa: BLE001
        _LOGGER.debug("Programmatic provisioning failed: %s", err)
        return False


async def _write_dashboard_storage(
    hass: HomeAssistant, inverter_sn: str
) -> None:
    """Write the dashboard config to HA storage."""
    config = get_dashboard_config(inverter_sn)

    storage_data = {
        "version": 1,
        "minor_version": 1,
        "key": f"lovelace.{DASHBOARD_URL_PATH}",
        "data": {"config": config},
    }

    storage_path = Path(hass.config.path(DASHBOARD_FILENAME))
    storage_path.parent.mkdir(parents=True, exist_ok=True)

    await hass.async_add_executor_job(
        json_helper.save_json, str(storage_path), storage_data
    )
    _LOGGER.info(
        "Sunsynk dashboard config written to %s", storage_path
    )
