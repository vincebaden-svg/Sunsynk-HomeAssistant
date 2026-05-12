"""Grid charge switch entity for Sunsynk."""
from __future__ import annotations

import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from ..coordinator import SunsynkCoordinator

_LOGGER = logging.getLogger(__name__)


class SunsynkGridChargeSwitchEntity(CoordinatorEntity[SunsynkCoordinator], SwitchEntity):
    """Switch to enable/disable grid charging."""

    _attr_has_entity_name = True
    _attr_name = "Grid Charge"

    def __init__(self, coordinator: SunsynkCoordinator) -> None:
        """Initialize the grid charge switch."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator._inverter_sn}_grid_charge"
        self._optimistic_state: bool | None = None

    @property
    def is_on(self) -> bool | None:
        """Return True if grid charging is enabled."""
        if self._optimistic_state is not None:
            return self._optimistic_state
        if self.coordinator.data is None:
            return None
        # Check time1on–time6on: if any timer is enabled, grid charge is "on"
        settings = self.coordinator.data.settings
        if not settings:
            return None
        # gridCharge field if it exists
        grid_charge = settings.get("gridCharge")
        if grid_charge is not None:
            return str(grid_charge) == "1" or grid_charge is True
        # Fall back to peakAndVallery (use timer = grid charge enabled)
        peak_valley = settings.get("peakAndVallery")
        if peak_valley is not None:
            return str(peak_valley) == "1" or peak_valley is True
        return None

    async def async_turn_on(self, **kwargs) -> None:
        """Enable grid charging."""
        self._optimistic_state = True
        self.async_write_ha_state()
        try:
            await self.coordinator.write_service.execute_write("grid_charge", True)
        except Exception:
            self._optimistic_state = None
            self.async_write_ha_state()
            raise
        finally:
            self._optimistic_state = None
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        """Disable grid charging."""
        self._optimistic_state = False
        self.async_write_ha_state()
        try:
            await self.coordinator.write_service.execute_write("grid_charge", False)
        except Exception:
            self._optimistic_state = None
            self.async_write_ha_state()
            raise
        finally:
            self._optimistic_state = None
        await self.coordinator.async_request_refresh()
