"""The Sunsynk Solar Inverter integration."""
from __future__ import annotations

from datetime import timedelta
import logging
from pathlib import Path
import shutil

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .api.official import OfficialApiClient
from .api.unofficial import UnofficialApiClient
from .const import (
    API_MODE_OFFICIAL,
    DOMAIN,
)
from .coordinator import SunsynkCoordinator
from .dashboard import async_provision_dashboard

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[str] = ["sensor", "binary_sensor", "switch", "select", "number"]


def _install_blueprints(hass: HomeAssistant) -> None:
    """Copy bundled blueprints to HA's blueprint directory (idempotent)."""
    source_dir = Path(__file__).parent / "blueprints"
    if not source_dir.exists():
        return

    target_dir = Path(hass.config.path("blueprints/automation/sunsynk"))
    target_dir.mkdir(parents=True, exist_ok=True)

    for blueprint_file in source_dir.glob("*.yaml"):
        target_file = target_dir / blueprint_file.name
        if not target_file.exists():
            shutil.copy2(blueprint_file, target_file)
            _LOGGER.info("Installed blueprint: %s", blueprint_file.name)
        else:
            _LOGGER.debug("Blueprint already exists: %s", blueprint_file.name)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Sunsynk from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    # Create the appropriate API client based on configured mode
    api_mode = entry.data.get("api_mode", "unofficial")
    inverter_sn = entry.data.get("inverter_sn", "")

    if api_mode == API_MODE_OFFICIAL:
        client = OfficialApiClient(
            app_key=entry.data["app_key"],
            app_secret=entry.data["app_secret"],
            inverter_sn=inverter_sn,
            username=entry.data.get("username", ""),
            password=entry.data.get("password", ""),
        )
    else:
        client = UnofficialApiClient(
            username=entry.data["username"],
            password=entry.data["password"],
            inverter_sn=inverter_sn,
            region=entry.data.get("region", "api.sunsynk.net"),
        )

    # Authenticate on setup
    await client.authenticate()

    # Create coordinator
    poll_interval = timedelta(
        minutes=entry.options.get("poll_interval_minutes", 5)
    )
    coordinator = SunsynkCoordinator(
        hass=hass,
        client=client,
        update_interval=poll_interval,
        inverter_sn=inverter_sn,
        soc_threshold=entry.options.get("soc_threshold", 20.0),
        solar_threshold=entry.options.get("solar_threshold", 500.0),
        summary_time=entry.options.get("summary_time", "18:00"),
    )

    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()

    # Initialize time-series storage
    db_path = hass.config.path(f"custom_components/sunsynk/{inverter_sn}.db")
    retention_days = entry.options.get("retention_days", 30)
    await coordinator.async_init_storage(db_path=db_path, retention_days=retention_days)

    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Auto-provision dashboard on first setup (idempotent)
    await async_provision_dashboard(hass, inverter_sn)

    # Install bundled blueprints to HA's blueprint directory (idempotent)
    await hass.async_add_executor_job(_install_blueprints, hass)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
