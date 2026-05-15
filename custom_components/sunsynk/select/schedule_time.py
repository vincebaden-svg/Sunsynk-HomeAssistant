"""Charging schedule time slot select entities for Sunsynk (6 slots)."""
from __future__ import annotations

import logging

from homeassistant.components.select import SelectEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from ..coordinator import SunsynkCoordinator

_LOGGER = logging.getLogger(__name__)

NUM_SLOTS = 6

TIME_OPTIONS = [
    "00:00", "00:30", "01:00", "01:30", "02:00", "02:30",
    "03:00", "03:30", "04:00", "04:30", "05:00", "05:30",
    "06:00", "06:30", "07:00", "07:30", "08:00", "08:30",
    "09:00", "09:30", "10:00", "10:30", "11:00", "11:30",
    "12:00", "12:30", "13:00", "13:30", "14:00", "14:30",
    "15:00", "15:30", "16:00", "16:30", "17:00", "17:30",
    "18:00", "18:30", "19:00", "19:30", "20:00", "20:30",
    "21:00", "21:30", "22:00", "22:30", "23:00", "23:30",
]


class SunsynkScheduleTimeSelect(CoordinatorEntity[SunsynkCoordinator], SelectEntity):
    """Select entity for a charging schedule time slot."""

    _attr_has_entity_name = True
    _attr_options = TIME_OPTIONS
    _attr_icon = "mdi:clock-outline"

    def __init__(self, coordinator: SunsynkCoordinator, slot: int) -> None:
        """Initialize the schedule time select."""
        super().__init__(coordinator)
        self._slot = slot
        self._attr_name = f"Program {slot} Time"
        self._attr_device_info = coordinator.device_info
        self._attr_unique_id = f"sunsynk_prog{slot}_time"
        self._optimistic_option: str | None = None

    @property
    def current_option(self) -> str | None:
        """Return the current time slot value from settings."""
        if self._optimistic_option is not None:
            return self._optimistic_option
        if self.coordinator.data is None:
            return None
        settings = self.coordinator.data.settings
        if not settings:
            return None
        val = settings.get(f"sellTime{self._slot}")
        if val is None or val == 0:
            return "00:00"
        return str(val) if str(val) in TIME_OPTIONS else None

    async def async_select_option(self, option: str) -> None:
        """Change the time slot."""
        if option not in TIME_OPTIONS:
            return
        self._optimistic_option = option
        self.async_write_ha_state()
        try:
            await self.coordinator.write_service.execute_write(
                f"sellTime{self._slot}", option
            )
        except Exception:
            self._optimistic_option = None
            self.async_write_ha_state()
            raise
        finally:
            self._optimistic_option = None
        await self.coordinator.async_request_refresh()


def create_schedule_time_entities(coordinator: SunsynkCoordinator) -> list:
    """Create all 6 schedule time select entities."""
    return [
        SunsynkScheduleTimeSelect(coordinator, slot)
        for slot in range(1, NUM_SLOTS + 1)
    ]
