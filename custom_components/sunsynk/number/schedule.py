"""Charging schedule number entities for Sunsynk (6 time slots)."""
from __future__ import annotations

import logging

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from ..coordinator import SunsynkCoordinator

_LOGGER = logging.getLogger(__name__)

NUM_SLOTS = 6


class SunsynkProgPowerNumber(CoordinatorEntity[SunsynkCoordinator], NumberEntity):
    """Number entity for charging schedule slot power limit."""

    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = "W"
    _attr_native_min_value = 0
    _attr_native_max_value = 8000
    _attr_native_step = 100
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator: SunsynkCoordinator, slot: int) -> None:
        """Initialize the prog power number."""
        super().__init__(coordinator)
        self._slot = slot
        self._attr_name = f"Program {slot} Power"
        self._attr_device_info = coordinator.device_info
        self._attr_unique_id = f"sunsynk_prog{slot}_power"
        self._optimistic_value: float | None = None

    @property
    def native_value(self) -> float | None:
        """Return current program power from settings."""
        if self._optimistic_value is not None:
            return self._optimistic_value
        if self.coordinator.data is None:
            return None
        settings = self.coordinator.data.settings
        if not settings:
            return None
        val = settings.get(f"sellTime{self._slot}Pac")
        if val is None:
            return None
        try:
            return float(val)
        except (ValueError, TypeError):
            return None

    async def async_set_native_value(self, value: float) -> None:
        """Set the power limit for this slot."""
        self._optimistic_value = value
        self.async_write_ha_state()
        try:
            await self.coordinator.write_service.execute_write(
                f"sellTime{self._slot}Pac", value
            )
        except Exception:
            self._optimistic_value = None
            self.async_write_ha_state()
            raise
        finally:
            self._optimistic_value = None
        await self.coordinator.async_request_refresh()


class SunsynkProgCapacityNumber(CoordinatorEntity[SunsynkCoordinator], NumberEntity):
    """Number entity for charging schedule slot SOC capacity."""

    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = "%"
    _attr_native_min_value = 0
    _attr_native_max_value = 100
    _attr_native_step = 1
    _attr_mode = NumberMode.SLIDER

    def __init__(self, coordinator: SunsynkCoordinator, slot: int) -> None:
        """Initialize the prog capacity number."""
        super().__init__(coordinator)
        self._slot = slot
        self._attr_name = f"Program {slot} SOC"
        self._attr_device_info = coordinator.device_info
        self._attr_unique_id = f"sunsynk_prog{slot}_capacity"
        self._optimistic_value: float | None = None

    @property
    def native_value(self) -> float | None:
        """Return current program SOC from settings."""
        if self._optimistic_value is not None:
            return self._optimistic_value
        if self.coordinator.data is None:
            return None
        settings = self.coordinator.data.settings
        if not settings:
            return None
        val = settings.get(f"cap{self._slot}")
        if val is None:
            return None
        try:
            return float(val)
        except (ValueError, TypeError):
            return None

    async def async_set_native_value(self, value: float) -> None:
        """Set the SOC capacity for this slot."""
        self._optimistic_value = value
        self.async_write_ha_state()
        try:
            await self.coordinator.write_service.execute_write(
                f"cap{self._slot}", value
            )
        except Exception:
            self._optimistic_value = None
            self.async_write_ha_state()
            raise
        finally:
            self._optimistic_value = None
        await self.coordinator.async_request_refresh()


def create_schedule_number_entities(
    coordinator: SunsynkCoordinator,
) -> list:
    """Create all 12 schedule number entities (6 slots × power + capacity)."""
    entities = []
    for slot in range(1, NUM_SLOTS + 1):
        entities.append(SunsynkProgPowerNumber(coordinator, slot))
        entities.append(SunsynkProgCapacityNumber(coordinator, slot))
    return entities
