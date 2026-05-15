"""Idempotent Lovelace dashboard provisioner for Sunsynk."""
from __future__ import annotations

import json
import logging
from pathlib import Path

from homeassistant.core import HomeAssistant

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

    Strategy:
    1. Try HA's programmatic lovelace dashboards API (works on most versions)
    2. Fallback: write .storage files directly using stdlib json
    """
    try:
        # Check if dashboard storage file already exists
        storage_path = Path(hass.config.path(DASHBOARD_FILENAME))
        if storage_path.exists():
            _LOGGER.debug(
                "Sunsynk dashboard storage already exists, skipping provisioning"
            )
            return

        # Try the programmatic approach first
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


def _read_json_file(path: Path) -> dict:
    """Read a JSON file, return empty dict if missing or invalid."""
    if not path.exists():
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _write_json_file(path: Path, data: dict) -> None:
    """Write a dict to a JSON file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


async def _write_dashboard_storage(
    hass: HomeAssistant, inverter_sn: str
) -> None:
    """Write the dashboard config and registration to HA storage."""
    config = get_dashboard_config(inverter_sn)

    # Write the dashboard view config
    storage_data = {
        "version": 1,
        "minor_version": 1,
        "key": f"lovelace.{DASHBOARD_URL_PATH}",
        "data": {"config": config},
    }

    storage_path = Path(hass.config.path(DASHBOARD_FILENAME))

    await hass.async_add_executor_job(_write_json_file, storage_path, storage_data)

    # Also register the dashboard in lovelace_dashboards so it appears in sidebar
    dashboards_path = Path(hass.config.path(".storage/lovelace_dashboards"))

    existing = await hass.async_add_executor_job(_read_json_file, dashboards_path)
    if not existing:
        existing = {
            "version": 1,
            "minor_version": 1,
            "key": "lovelace_dashboards",
            "data": {"items": []},
        }

    # Check if already registered
    items = existing.get("data", {}).get("items", [])
    for item in items:
        if item.get("url_path") == DASHBOARD_URL_PATH:
            _LOGGER.debug("Dashboard already registered in lovelace_dashboards")
            return

    # Add our dashboard
    items.append({
        "id": DASHBOARD_URL_PATH,
        "url_path": DASHBOARD_URL_PATH,
        "title": DASHBOARD_TITLE,
        "icon": "mdi:solar-power",
        "show_in_sidebar": True,
        "require_admin": False,
        "mode": "storage",
    })
    existing.setdefault("data", {})["items"] = items

    await hass.async_add_executor_job(_write_json_file, dashboards_path, existing)
    _LOGGER.info(
        "Sunsynk dashboard registered and config written. "
        "Restart HA to see it in sidebar."
    )
