"""Select platform for Sunsynk Solar Inverter."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from ..const import DOMAIN
from ..coordinator import SunsynkCoordinator
from .battery_priority import SunsynkBatteryPrioritySelect
from .schedule_time import create_schedule_time_entities
from .work_mode import SunsynkWorkModeSelect


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Sunsynk select entities."""
    coordinator: SunsynkCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        SunsynkBatteryPrioritySelect(coordinator),
        SunsynkWorkModeSelect(coordinator),
    ]
    entities.extend(create_schedule_time_entities(coordinator))

    async_add_entities(entities)
