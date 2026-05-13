"""Charge and discharge current number entities for Sunsynk."""
from __future__ import annotations

import logging

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.const import UnitOfElectricCurrent
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from ..coordinator import SunsynkCoordinator

_LOGGER = logging.getLogger(__name__)

MAX_CURRENT = 185.0  # A — conservative max; actual max depends on inverter model


class SunsynkChargeCurrentNumber(CoordinatorEntity[SunsynkCoordinator], NumberEntity):
    """Number entity for battery maximum charge current."""

    _attr_has_entity_name = True
    _attr_name = "Max Charge Current"
    _attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
    _attr_native_min_value = 0.0
    _attr_native_max_value = MAX_CURRENT
    _attr_native_step = 1.0
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator: SunsynkCoordinator) -> None:
        """Initialize the charge current number."""
        super().__init__(coordinator)
        self._attr_device_info = coordinator.device_info
        self._attr_unique_id = f"sunsynk_charge_current"
        self._optimistic_value: float | None = None

    @property
    def native_value(self) -> float | None:
        """Return the current charge current limit from settings."""
        if self._optimistic_value is not None:
            return self._optimistic_value
        if self.coordinator.data is None:
            return None
        settings = self.coordinator.data.settings
        if not settings:
            return None
        val = settings.get("batteryMaxCurrentCharge")
        if val is None:
            return None
        try:
            return float(val)
        except (ValueError, TypeError):
            return None

    async def async_set_native_value(self, value: float) -> None:
        """Set the maximum charge current."""
        self._optimistic_value = value
        self.async_write_ha_state()
        try:
            await self.coordinator.write_service.execute_write("charge_current", value)
        except Exception:
            self._optimistic_value = None
            self.async_write_ha_state()
            raise
        finally:
            self._optimistic_value = None
        await self.coordinator.async_request_refresh()


class SunsynkDischargeCurrentNumber(CoordinatorEntity[SunsynkCoordinator], NumberEntity):
    """Number entity for battery maximum discharge current."""

    _attr_has_entity_name = True
    _attr_name = "Max Discharge Current"
    _attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
    _attr_native_min_value = 0.0
    _attr_native_max_value = MAX_CURRENT
    _attr_native_step = 1.0
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator: SunsynkCoordinator) -> None:
        """Initialize the discharge current number."""
        super().__init__(coordinator)
        self._attr_device_info = coordinator.device_info
        self._attr_unique_id = f"sunsynk_discharge_current"
        self._optimistic_value: float | None = None

    @property
    def native_value(self) -> float | None:
        """Return the current discharge current limit from settings."""
        if self._optimistic_value is not None:
            return self._optimistic_value
        if self.coordinator.data is None:
            return None
        settings = self.coordinator.data.settings
        if not settings:
            return None
        val = settings.get("batteryMaxCurrentDischarge")
        if val is None:
            return None
        try:
            return float(val)
        except (ValueError, TypeError):
            return None

    async def async_set_native_value(self, value: float) -> None:
        """Set the maximum discharge current."""
        self._optimistic_value = value
        self.async_write_ha_state()
        try:
            await self.coordinator.write_service.execute_write("discharge_current", value)
        except Exception:
            self._optimistic_value = None
            self.async_write_ha_state()
            raise
        finally:
            self._optimistic_value = None
        await self.coordinator.async_request_refresh()
