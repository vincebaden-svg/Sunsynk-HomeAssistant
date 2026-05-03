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
        # Actual grid_charge state field to be confirmed via API spike task
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
