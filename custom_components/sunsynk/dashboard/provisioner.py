"""Idempotent Lovelace dashboard provisioner for Sunsynk."""
from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant

from .layout import get_dashboard_config

_LOGGER = logging.getLogger(__name__)

DASHBOARD_URL_PATH = "sunsynk"
DASHBOARD_TITLE = "Sunsynk Solar"


async def async_provision_dashboard(
    hass: HomeAssistant,
    inverter_sn: str,
) -> None:
    """Create the Sunsynk Lovelace dashboard if it doesn't already exist.

    This function is idempotent — calling it multiple times is safe.
    """
    try:
        # Check if dashboard already exists
        dashboards = await _get_existing_dashboards(hass)

        for dashboard in dashboards:
            if dashboard.get("url_path") == DASHBOARD_URL_PATH:
                _LOGGER.debug(
                    "Sunsynk dashboard already exists at /%s, skipping provisioning",
                    DASHBOARD_URL_PATH,
                )
                return

        # Create the dashboard
        await _create_dashboard(hass, inverter_sn)
        _LOGGER.info("Sunsynk dashboard provisioned at /%s", DASHBOARD_URL_PATH)

    except Exception as err:  # noqa: BLE001
        _LOGGER.warning(
            "Failed to provision Sunsynk dashboard: %s. "
            "You can create it manually using the layout in dashboard/layout.py",
            err,
        )


async def _get_existing_dashboards(hass: HomeAssistant) -> list[dict]:
    """Get list of existing Lovelace dashboards."""
    try:
        lovelace = hass.data.get("lovelace")
        if lovelace is None:
            return []

        # Try to get dashboards via the lovelace storage
        dashboards_collection = getattr(lovelace, "dashboards", None)
        if dashboards_collection is None:
            return []

        return list(dashboards_collection.async_items())
    except Exception:  # noqa: BLE001
        return []


async def _create_dashboard(hass: HomeAssistant, inverter_sn: str) -> None:
    """Create the Sunsynk Lovelace dashboard."""
    config = get_dashboard_config(inverter_sn)

    try:
        lovelace = hass.data.get("lovelace")
        if lovelace is None:
            _LOGGER.warning("Lovelace not available — dashboard not provisioned")
            return

        dashboards_collection = getattr(lovelace, "dashboards", None)
        if dashboards_collection is None:
            _LOGGER.warning("Lovelace dashboards collection not available")
            return

        await dashboards_collection.async_create_item({
            "url_path": DASHBOARD_URL_PATH,
            "title": DASHBOARD_TITLE,
            "icon": "mdi:solar-power",
            "show_in_sidebar": True,
            "require_admin": False,
            "mode": "storage",
        })

        _LOGGER.info("Sunsynk dashboard created successfully")

    except Exception as err:  # noqa: BLE001
        _LOGGER.warning("Could not create dashboard via API: %s", err)
