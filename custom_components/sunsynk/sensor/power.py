"""Power and battery sensor entities for Sunsynk."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, UnitOfElectricCurrent, UnitOfElectricPotential, UnitOfPower
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from ..api.base import SunsynkData
from ..const import SENSOR_VALID_RANGES
from ..coordinator import SunsynkCoordinator

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class SunsynkSensorEntityDescription(SensorEntityDescription):
    """Extended sensor description with value accessor."""

    value_fn: Callable[[SunsynkData], float | None] = lambda _: None


POWER_SENSORS: tuple[SunsynkSensorEntityDescription, ...] = (
    SunsynkSensorEntityDescription(
        key="pv_power",
        name="PV Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.pv_power,
    ),
    SunsynkSensorEntityDescription(
        key="battery_power",
        name="Battery Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.battery_power,
    ),
    SunsynkSensorEntityDescription(
        key="battery_voltage",
        name="Battery Voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.battery_voltage,
    ),
    SunsynkSensorEntityDescription(
        key="battery_current",
        name="Battery Current",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.battery_current,
    ),
    SunsynkSensorEntityDescription(
        key="battery_soc",
        name="Battery SOC",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.battery_soc,
    ),
    SunsynkSensorEntityDescription(
        key="grid_power",
        name="Grid Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.grid_power,
    ),
    SunsynkSensorEntityDescription(
        key="load_power",
        name="Load Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.load_power,
    ),
)

# PV string sensors — created dynamically based on user config
PV_STRING_SENSORS: dict[int, SunsynkSensorEntityDescription] = {
    1: SunsynkSensorEntityDescription(
        key="pv1_power",
        name="PV1 Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.pv1_power,
    ),
    2: SunsynkSensorEntityDescription(
        key="pv2_power",
        name="PV2 Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.pv2_power,
    ),
    3: SunsynkSensorEntityDescription(
        key="pv3_power",
        name="PV3 Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.pv3_power,
    ),
    4: SunsynkSensorEntityDescription(
        key="pv4_power",
        name="PV4 Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.pv4_power,
    ),
}


class SunsynkPowerSensor(CoordinatorEntity[SunsynkCoordinator], SensorEntity):
    """A Sunsynk power/battery sensor entity."""

    entity_description: SunsynkSensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: SunsynkCoordinator,
        description: SunsynkSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator._inverter_sn}_{description.key}"
        self._last_valid_value: float | None = None

    @property
    def native_value(self) -> float | None:
        """Return the sensor value, rejecting out-of-range data."""
        if self.coordinator.data is None:
            return self._last_valid_value

        raw = self.entity_description.value_fn(self.coordinator.data)
        if raw is None:
            return self._last_valid_value

        # Validate against known safe ranges
        key = self.entity_description.key
        if key in SENSOR_VALID_RANGES:
            lo, hi = SENSOR_VALID_RANGES[key]
            if not (lo <= raw <= hi):
                _LOGGER.warning(
                    "Out-of-range value for %s: %s (valid range: %s-%s) — retaining last valid value",
                    key, raw, lo, hi,
                )
                return self._last_valid_value

        self._last_valid_value = raw
        return raw
