"""Charging schedule grid/gen charge switches for Sunsynk (6 slots + global timer)."""
from __future__ import annotations

import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from ..coordinator import SunsynkCoordinator

_LOGGER = logging.getLogger(__name__)

NUM_SLOTS = 6


class SunsynkUseTimerSwitch(CoordinatorEntity[SunsynkCoordinator], SwitchEntity):
    """Global switch to enable/disable the timer system (peakAndVallery)."""

    _attr_has_entity_name = True
    _attr_name = "Use Timer"
    _attr_icon = "mdi:timer-check"

    def __init__(self, coordinator: SunsynkCoordinator) -> None:
        """Initialize the use timer switch."""
        super().__init__(coordinator)
        self._attr_device_info = coordinator.device_info
        self._attr_unique_id = "sunsynk_use_timer"
        self._optimistic_state: bool | None = None

    @property
    def is_on(self) -> bool | None:
        """Return True if timer is enabled."""
        if self._optimistic_state is not None:
            return self._optimistic_state
        if self.coordinator.data is None:
            return None
        settings = self.coordinator.data.settings
        if not settings:
            return None
        val = settings.get("peakAndVallery")
        if val is None:
            return None
        if isinstance(val, bool):
            return val
        return str(val).lower() in ("true", "1")

    async def async_turn_on(self, **kwargs) -> None:
        """Enable timer."""
        self._optimistic_state = True
        self.async_write_ha_state()
        try:
            await self.coordinator.write_service.execute_write("peakAndVallery", True)
        except Exception:
            self._optimistic_state = None
            self.async_write_ha_state()
            raise
        finally:
            self._optimistic_state = None
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        """Disable timer."""
        self._optimistic_state = False
        self.async_write_ha_state()
        try:
            await self.coordinator.write_service.execute_write("peakAndVallery", False)
        except Exception:
            self._optimistic_state = None
            self.async_write_ha_state()
            raise
        finally:
            self._optimistic_state = None
        await self.coordinator.async_request_refresh()


class SunsynkGridChargeSlotSwitch(CoordinatorEntity[SunsynkCoordinator], SwitchEntity):
    """Switch for grid charge per time slot."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:transmission-tower-import"

    def __init__(self, coordinator: SunsynkCoordinator, slot: int) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._slot = slot
        self._attr_name = f"Program {slot} Grid Charge"
        self._attr_device_info = coordinator.device_info
        self._attr_unique_id = f"sunsynk_prog{slot}_grid_charge"
        self._optimistic_state: bool | None = None

    @property
    def is_on(self) -> bool | None:
        """Return True if grid charge is enabled for this slot."""
        if self._optimistic_state is not None:
            return self._optimistic_state
        if self.coordinator.data is None:
            return None
        settings = self.coordinator.data.settings
        if not settings:
            return None
        # The API field might be gridTime{N}on or time{N}on for grid
        # Based on the Node-RED flow, grid charge uses time{N}on
        # and gen uses genTime{N}on. Let's check for a dedicated grid field.
        # Actually from the settings dump, there's no separate gridTime field.
        # The "Grid" checkbox on the inverter maps to time{N}on (already used for "enabled")
        # Re-examining: time{N}on = slot enabled, but the Grid checkbox is separate.
        # Looking at the API fields more carefully:
        # time1on = grid charge enabled for slot 1
        # genTime1on = gen charge enabled for slot 1
        # The "enabled" concept IS the grid charge checkbox.
        # So our existing "Program N Enabled" IS the grid charge toggle.
        # Let me map this correctly:
        val = settings.get(f"time{self._slot}on")
        if val is None:
            return None
        if isinstance(val, bool):
            return val
        return str(val).lower() in ("true", "1")

    async def async_turn_on(self, **kwargs) -> None:
        """Enable grid charge for this slot."""
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
        """Disable grid charge for this slot."""
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


class SunsynkGenChargeSlotSwitch(CoordinatorEntity[SunsynkCoordinator], SwitchEntity):
    """Switch for generator charge per time slot."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:engine"

    def __init__(self, coordinator: SunsynkCoordinator, slot: int) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._slot = slot
        self._attr_name = f"Program {slot} Gen Charge"
        self._attr_device_info = coordinator.device_info
        self._attr_unique_id = f"sunsynk_prog{slot}_gen_charge"
        self._optimistic_state: bool | None = None

    @property
    def is_on(self) -> bool | None:
        """Return True if gen charge is enabled for this slot."""
        if self._optimistic_state is not None:
            return self._optimistic_state
        if self.coordinator.data is None:
            return None
        settings = self.coordinator.data.settings
        if not settings:
            return None
        val = settings.get(f"genTime{self._slot}on")
        if val is None:
            return None
        if isinstance(val, bool):
            return val
        return str(val).lower() in ("true", "1")

    async def async_turn_on(self, **kwargs) -> None:
        """Enable gen charge for this slot."""
        self._optimistic_state = True
        self.async_write_ha_state()
        try:
            await self.coordinator.write_service.execute_write(
                f"genTime{self._slot}on", True
            )
        except Exception:
            self._optimistic_state = None
            self.async_write_ha_state()
            raise
        finally:
            self._optimistic_state = None
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        """Disable gen charge for this slot."""
        self._optimistic_state = False
        self.async_write_ha_state()
        try:
            await self.coordinator.write_service.execute_write(
                f"genTime{self._slot}on", False
            )
        except Exception:
            self._optimistic_state = None
            self.async_write_ha_state()
            raise
        finally:
            self._optimistic_state = None
        await self.coordinator.async_request_refresh()


def create_schedule_charge_entities(coordinator: SunsynkCoordinator) -> list:
    """Create use timer + 6 grid charge + 6 gen charge switches."""
    entities = [SunsynkUseTimerSwitch(coordinator)]
    for slot in range(1, NUM_SLOTS + 1):
        entities.append(SunsynkGridChargeSlotSwitch(coordinator, slot))
        entities.append(SunsynkGenChargeSlotSwitch(coordinator, slot))
    return entities
