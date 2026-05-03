"""Energy total sensor entities for Sunsynk."""
from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.const import UnitOfEnergy

from .power import SunsynkPowerSensor, SunsynkSensorEntityDescription

ENERGY_SENSORS: tuple[SunsynkSensorEntityDescription, ...] = (
    # Today
    SunsynkSensorEntityDescription(
        key="pv_energy_today",
        name="PV Energy Today",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda data: data.pv_energy_today,
    ),
    SunsynkSensorEntityDescription(
        key="battery_charge_today",
        name="Battery Charge Today",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda data: data.battery_charge_today,
    ),
    SunsynkSensorEntityDescription(
        key="battery_discharge_today",
        name="Battery Discharge Today",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda data: data.battery_discharge_today,
    ),
    SunsynkSensorEntityDescription(
        key="grid_import_today",
        name="Grid Import Today",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda data: data.grid_import_today,
    ),
    SunsynkSensorEntityDescription(
        key="grid_export_today",
        name="Grid Export Today",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda data: data.grid_export_today,
    ),
    SunsynkSensorEntityDescription(
        key="load_energy_today",
        name="Load Energy Today",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda data: data.load_energy_today,
    ),
    # Month
    SunsynkSensorEntityDescription(
        key="pv_energy_month",
        name="PV Energy Month",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda data: data.pv_energy_month,
    ),
    SunsynkSensorEntityDescription(
        key="grid_import_month",
        name="Grid Import Month",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda data: data.grid_import_month,
    ),
    SunsynkSensorEntityDescription(
        key="load_energy_month",
        name="Load Energy Month",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda data: data.load_energy_month,
    ),
    # Year
    SunsynkSensorEntityDescription(
        key="pv_energy_year",
        name="PV Energy Year",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda data: data.pv_energy_year,
    ),
    SunsynkSensorEntityDescription(
        key="grid_import_year",
        name="Grid Import Year",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda data: data.grid_import_year,
    ),
    SunsynkSensorEntityDescription(
        key="load_energy_year",
        name="Load Energy Year",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda data: data.load_energy_year,
    ),
)

# Re-export SunsynkPowerSensor for use as energy sensor (same class, different description)
SunsynkEnergySensor = SunsynkPowerSensor
