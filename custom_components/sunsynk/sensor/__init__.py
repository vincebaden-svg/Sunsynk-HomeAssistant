"""Sensor platform for Sunsynk Solar Inverter."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from ..const import DOMAIN
from ..coordinator import SunsynkCoordinator
from .energy import ENERGY_SENSORS, SunsynkEnergySensor
from .power import POWER_SENSORS, PV_STRING_SENSORS, SunsynkPowerSensor
from .status import (
    SunsynkFaultCodeSensor,
    SunsynkLastPolledSensor,
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

    # Get configured number of PV strings (default 2)
    pv_strings = entry.options.get("pv_strings", 2)

    entities: list = [
        SunsynkPowerSensor(coordinator, description)
        for description in POWER_SENSORS
    ]

    # Add PV string sensors based on user configuration
    for string_num in range(1, pv_strings + 1):
        if string_num in PV_STRING_SENSORS:
            entities.append(
                SunsynkPowerSensor(coordinator, PV_STRING_SENSORS[string_num])
            )

    entities.extend(
        SunsynkEnergySensor(coordinator, description)
        for description in ENERGY_SENSORS
    )
    entities.extend([
        SunsynkFaultCodeSensor(coordinator),
        SunsynkSystemStatusSensor(coordinator),
        SunsynkWeatherTemperatureSensor(coordinator),
        SunsynkWeatherDescriptionSensor(coordinator),
        SunsynkLastPolledSensor(coordinator),
    ])

    async_add_entities(entities)
