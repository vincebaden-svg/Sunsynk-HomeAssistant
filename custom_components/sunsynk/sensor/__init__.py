"""Sensor platform for Sunsynk Solar Inverter."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from ..const import DOMAIN
from ..coordinator import SunsynkCoordinator
from .energy import ENERGY_SENSORS, SunsynkEnergySensor
from .power import POWER_SENSORS, SunsynkPowerSensor
from .status import (
    SunsynkFaultCodeSensor,
    SunsynkSystemStatusSensor,
    SunsynkWeatherDescriptionSensor,
    SunsynkWeatherTemperatureSensor,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Sunsynk sensor entities."""
    coordinator: SunsynkCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list = [
        SunsynkPowerSensor(coordinator, description)
        for description in POWER_SENSORS
    ]
    entities.extend(
        SunsynkEnergySensor(coordinator, description)
        for description in ENERGY_SENSORS
    )
    entities.extend([
        SunsynkFaultCodeSensor(coordinator),
        SunsynkSystemStatusSensor(coordinator),
        SunsynkWeatherTemperatureSensor(coordinator),
        SunsynkWeatherDescriptionSensor(coordinator),
    ])

    async_add_entities(entities)
