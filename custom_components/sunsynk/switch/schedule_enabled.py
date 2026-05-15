"""Charging schedule enabled switch entities for Sunsynk (6 slots)."""
from __future__ import annotations

import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from ..coordinator import SunsynkCoordinator

_LOGGER = logging.getLogger(__name__)

NUM_SLOTS = 6


class SunsynkScheduleEnabledSwitch(CoordinatorEntity[SunsynkCoordinator], SwitchEntity):
    """Switch to enable/disable a charging schedule time slot."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:timer-outline"

    def __init__(self, coordinator: SunsynkCoordinator, slot: int) -> None:
        """Initialize the schedule enabled switch."""
        super().__init__(coordinator)
        self._slot = slot
        self._attr_name = f"Program {slot} Enabled"
        self._attr_device_info = coordinator.device_info
        self._attr_unique_id = f"sunsynk_prog{slot}_enabled"
        self._optimistic_state: bool | None = None

    @property
    def is_on(self) -> bool | None:
        """Return True if this time slot is enabled."""
        if self._optimistic_state is not None:
            return self._optimistic_state
        if self.coordinator.data is None:
            return None
        settings = self.coordinator.data.settings
        if not settings:
            return None
        val = settings.get(f"time{self._slot}on")
        if val is None:
            return None
        # API returns true/false, "true"/"false", 1/0, or "1"/"0"
        if isinstance(val, bool):
            return val
        return str(val).lower() in ("true", "1")

    async def async_turn_on(self, **kwargs) -> None:
        """Enable this time slot."""
        self._optimistic_state = True
        self.async_write_ha_state()
        try:
            await self.coordinator.write_service.execute_write(
                f"time{self._slot}on", True
            )
        except Exception:
            self._optimistic_state = None
            self.async_write_ha_state()
            raise
        finally:
            self._optimistic_state = None
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        """Disable this time slot."""
        self._optimistic_state = False
        self.async_write_ha_state()
        try:
            await self.coordinator.write_service.execute_write(
                f"time{self._slot}on", False
            )
        except Exception:
            self._optimistic_state = None
            self.async_write_ha_state()
            raise
        finally:
            self._optimistic_state = None
        await self.coordinator.async_request_refresh()


def create_schedule_enabled_entities(coordinator: SunsynkCoordinator) -> list:
    """Create all 6 schedule enabled switch entities."""
    return [
        SunsynkScheduleEnabledSwitch(coordinator, slot)
        for slot in range(1, NUM_SLOTS + 1)
    ]
