"""Battery priority select entity for Sunsynk."""
from __future__ import annotations

import logging

from homeassistant.components.select import SelectEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from ..coordinator import SunsynkCoordinator

_LOGGER = logging.getLogger(__name__)

BATTERY_PRIORITY_OPTIONS = ["battery", "load"]


class SunsynkBatteryPrioritySelect(CoordinatorEntity[SunsynkCoordinator], SelectEntity):
    """Select entity for battery/load priority mode."""

    _attr_has_entity_name = True
    _attr_name = "Battery Priority"
    _attr_options = BATTERY_PRIORITY_OPTIONS

    def __init__(self, coordinator: SunsynkCoordinator) -> None:
        """Initialize the battery priority select."""
        super().__init__(coordinator)
        self._attr_device_info = coordinator.device_info
        self._attr_unique_id = f"sunsynk_battery_priority"
        self._optimistic_option: str | None = None

    @property
    def current_option(self) -> str | None:
        """Return the current priority mode from API settings."""
        if self._optimistic_option is not None:
            return self._optimistic_option
        if self.coordinator.data is None:
            return None
        energy_mode = self.coordinator.data.settings.get("energyMode")
        if energy_mode is None:
            return None
        # energyMode: 0 = battery priority, 1 = load priority
        return "battery" if str(energy_mode) == "0" else "load"

    async def async_select_option(self, option: str) -> None:
        """Change the battery priority mode."""
        if option not in BATTERY_PRIORITY_OPTIONS:
            return
        self._optimistic_option = option
        self.async_write_ha_state()
        try:
            await self.coordinator.write_service.execute_write("battery_priority", option)
        except Exception:
            self._optimistic_option = None
            self.async_write_ha_state()
            raise
        finally:
            self._optimistic_option = None
        await self.coordinator.async_request_refresh()
