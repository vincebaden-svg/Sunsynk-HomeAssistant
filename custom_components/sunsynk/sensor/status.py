"""Status and weather sensor entities for Sunsynk."""
from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import UnitOfTemperature
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from ..coordinator import SunsynkCoordinator


class SunsynkFaultCodeSensor(CoordinatorEntity[SunsynkCoordinator], SensorEntity):
    """Sensor showing current inverter fault code."""

    _attr_has_entity_name = True
    _attr_name = "Fault Code"

    def __init__(self, coordinator: SunsynkCoordinator) -> None:
        """Initialize the fault code sensor."""
        super().__init__(coordinator)
        self._attr_device_info = coordinator.device_info
        self._attr_unique_id = f"sunsynk_fault_code"

    @property
    def native_value(self) -> str:
        """Return current fault code or 'none'."""
        if self.coordinator.data is None:
            return "none"
        return self.coordinator.data.fault_code or "none"


class SunsynkSystemStatusSensor(CoordinatorEntity[SunsynkCoordinator], SensorEntity):
    """Sensor showing inverter system status."""

    _attr_has_entity_name = True
    _attr_name = "System Status"

    def __init__(self, coordinator: SunsynkCoordinator) -> None:
        """Initialize the system status sensor."""
        super().__init__(coordinator)
        self._attr_device_info = coordinator.device_info
        self._attr_unique_id = f"sunsynk_system_status"

    @property
    def native_value(self) -> str | None:
        """Return current system status."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.system_status


class SunsynkWeatherTemperatureSensor(CoordinatorEntity[SunsynkCoordinator], SensorEntity):
    """Sensor showing weather temperature at plant location."""

    _attr_has_entity_name = True
    _attr_name = "Weather Temperature"
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: SunsynkCoordinator) -> None:
        """Initialize the weather temperature sensor."""
        super().__init__(coordinator)
        self._attr_device_info = coordinator.device_info
        self._attr_unique_id = f"sunsynk_weather_temperature"

    @property
    def native_value(self) -> float | None:
        """Return current temperature."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.weather_temperature


class SunsynkWeatherDescriptionSensor(CoordinatorEntity[SunsynkCoordinator], SensorEntity):
    """Sensor showing weather description at plant location."""

    _attr_has_entity_name = True
    _attr_name = "Weather Description"

    def __init__(self, coordinator: SunsynkCoordinator) -> None:
        """Initialize the weather description sensor."""
        super().__init__(coordinator)
        self._attr_device_info = coordinator.device_info
        self._attr_unique_id = f"sunsynk_weather_description"

    @property
    def native_value(self) -> str | None:
        """Return current weather description."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.weather_description


class SunsynkLastPolledSensor(CoordinatorEntity[SunsynkCoordinator], SensorEntity):
    """Sensor showing when the API was last successfully polled."""

    _attr_has_entity_name = True
    _attr_name = "Last Polled"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:clock-check-outline"

    def __init__(self, coordinator: SunsynkCoordinator) -> None:
        """Initialize the last polled sensor."""
        super().__init__(coordinator)
        self._attr_device_info = coordinator.device_info
        self._attr_unique_id = f"sunsynk_last_polled"

    @property
    def native_value(self):
        """Return the timestamp of the last successful data fetch."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.last_updated
