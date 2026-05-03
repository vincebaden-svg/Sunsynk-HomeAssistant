"""Binary sensor platform for Sunsynk Solar Inverter."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from ..const import DOMAIN
from ..coordinator import SunsynkCoordinator
from .grid import SunsynkGridConnectedSensor


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Sunsynk binary sensor entities."""
    coordinator: SunsynkCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([SunsynkGridConnectedSensor(coordinator)])
