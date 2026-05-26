"""Switch platform for Sunsynk Solar Inverter."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from ..const import DOMAIN
from ..coordinator import SunsynkCoordinator
from .grid_charge import SunsynkGridChargeSwitchEntity
from .schedule_charge import create_schedule_charge_entities


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Sunsynk switch entities."""
    coordinator: SunsynkCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [SunsynkGridChargeSwitchEntity(coordinator)]
    entities.extend(create_schedule_charge_entities(coordinator))

    async_add_entities(entities)
