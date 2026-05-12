"""Work mode select entity for Sunsynk."""
from __future__ import annotations

import logging

from homeassistant.components.select import SelectEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from ..coordinator import SunsynkCoordinator

_LOGGER = logging.getLogger(__name__)

WORK_MODE_OPTIONS = ["self_use", "time_of_use", "backup", "peak_shaving"]


class SunsynkWorkModeSelect(CoordinatorEntity[SunsynkCoordinator], SelectEntity):
    """Select entity for inverter work mode."""

    _attr_has_entity_name = True
    _attr_name = "Work Mode"
    _attr_options = WORK_MODE_OPTIONS

    def __init__(self, coordinator: SunsynkCoordinator) -> None:
        """Initialize the work mode select."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator._inverter_sn}_work_mode"
        self._optimistic_option: str | None = None

    @property
    def current_option(self) -> str | None:
        """Return the current work mode from API settings."""
        if self._optimistic_option is not None:
            return self._optimistic_option
        if self.coordinator.data is None:
            return None
        sys_work_mode = self.coordinator.data.settings.get("sysWorkMode")
        if sys_work_mode is None:
            return None
        # sysWorkMode: 1=self_use, 2=time_of_use, 3=backup, 4=peak_shaving
        mode_map = {"1": "self_use", "2": "time_of_use", "3": "backup", "4": "peak_shaving"}
        return mode_map.get(str(sys_work_mode), str(sys_work_mode))

    async def async_select_option(self, option: str) -> None:
        """Change the work mode."""
        if option not in WORK_MODE_OPTIONS:
            return
        self._optimistic_option = option
        self.async_write_ha_state()
        try:
            await self.coordinator.write_service.execute_write("work_mode", option)
        except Exception:
            self._optimistic_option = None
            self.async_write_ha_state()
            raise
        finally:
            self._optimistic_option = None
        await self.coordinator.async_request_refresh()
