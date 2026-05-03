"""Number platform for Sunsynk Solar Inverter."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from ..const import DOMAIN
from ..coordinator import SunsynkCoordinator
from .current import SunsynkChargeCurrentNumber, SunsynkDischargeCurrentNumber
from .generator import GENERATOR_NUMBERS, SunsynkGeneratorNumber
from .schedule import create_schedule_number_entities


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Sunsynk number entities."""
    coordinator: SunsynkCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list = [
        SunsynkChargeCurrentNumber(coordinator),
        SunsynkDischargeCurrentNumber(coordinator),
    ]

    # Generator/AUX parameter entities (Tier 3 — confirmation required)
    entities.extend(
        SunsynkGeneratorNumber(coordinator, description)
        for description in GENERATOR_NUMBERS
    )

    # Charging schedule entities (6 slots × power + capacity)
    entities.extend(create_schedule_number_entities(coordinator))

    async_add_entities(entities)
