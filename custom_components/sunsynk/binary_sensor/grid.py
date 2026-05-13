"""Grid connection binary sensor and event dispatcher for Sunsynk."""
from __future__ import annotations

from datetime import datetime
import logging

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from ..coordinator import SunsynkCoordinator

_LOGGER = logging.getLogger(__name__)

EVENT_GRID_FAILURE = "sunsynk_grid_failure"
EVENT_GRID_RESTORED = "sunsynk_grid_restored"


class SunsynkGridConnectedSensor(CoordinatorEntity[SunsynkCoordinator], BinarySensorEntity):
    """Binary sensor tracking grid connection state.

    Also fires HA events on state transitions for automation triggers.
    """

    _attr_has_entity_name = True
    _attr_name = "Grid Connected"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(self, coordinator: SunsynkCoordinator) -> None:
        """Initialize the grid connected sensor."""
        super().__init__(coordinator)
        self._attr_device_info = coordinator.device_info
        self._attr_unique_id = f"sunsynk_grid_connected"
        self._previous_state: bool | None = None

    @property
    def is_on(self) -> bool:
        """Return True if grid is connected."""
        if self.coordinator.data is None:
            return False
        return self.coordinator.data.grid_connected

    def _handle_coordinator_update(self) -> None:
        """Handle updated data from coordinator and fire events on state change."""
        if self.coordinator.data is None:
            super()._handle_coordinator_update()
            return

        current_state = self.coordinator.data.grid_connected

        if self._previous_state is not None and current_state != self._previous_state:
            payload = {
                "inverter_sn": self.coordinator._inverter_sn,
                "battery_soc": self.coordinator.data.battery_soc,
                "timestamp": datetime.now().isoformat(),
            }

            if not current_state:
                # Grid just failed
                _LOGGER.warning(
                    "Grid failure detected for inverter %s (battery SOC: %s%%)",
                    self.coordinator._inverter_sn,
                    self.coordinator.data.battery_soc,
                )
                self.hass.bus.async_fire(EVENT_GRID_FAILURE, payload)
            else:
                # Grid just restored
                _LOGGER.info(
                    "Grid restored for inverter %s (battery SOC: %s%%)",
                    self.coordinator._inverter_sn,
                    self.coordinator.data.battery_soc,
                )
                self.hass.bus.async_fire(EVENT_GRID_RESTORED, payload)

        self._previous_state = current_state
        super()._handle_coordinator_update()
