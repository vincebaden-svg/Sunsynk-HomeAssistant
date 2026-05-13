"""Generator/AUX parameter number entities for Sunsynk."""
from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.number import NumberEntity, NumberEntityDescription, NumberMode
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from ..coordinator import SunsynkCoordinator

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class SunsynkNumberEntityDescription(NumberEntityDescription):
    """Extended number description with write key."""
    write_key: str = ""


GENERATOR_NUMBERS: tuple[SunsynkNumberEntityDescription, ...] = (
    SunsynkNumberEntityDescription(
        key="gen_peak_power",
        name="Generator Peak-Shaving Power",
        native_unit_of_measurement="W",
        native_min_value=500,
        native_max_value=30000,
        native_step=100,
        mode=NumberMode.BOX,
        write_key="genPeakPower",
    ),
    SunsynkNumberEntityDescription(
        key="gen_off_cap",
        name="Generator OFF SOC",
        native_unit_of_measurement="%",
        native_min_value=0,
        native_max_value=100,
        native_step=1,
        mode=NumberMode.SLIDER,
        write_key="genOffCap",
    ),
    SunsynkNumberEntityDescription(
        key="gen_on_cap",
        name="Generator ON SOC",
        native_unit_of_measurement="%",
        native_min_value=0,
        native_max_value=100,
        native_step=1,
        mode=NumberMode.SLIDER,
        write_key="genOnCap",
    ),
    SunsynkNumberEntityDescription(
        key="gen_min_solar",
        name="Generator Minimum Solar Power",
        native_unit_of_measurement="W",
        native_min_value=0,
        native_max_value=10000,
        native_step=100,
        mode=NumberMode.BOX,
        write_key="genMinSolar",
    ),
    SunsynkNumberEntityDescription(
        key="gen_off_volt",
        name="Generator OFF Voltage",
        native_unit_of_measurement="V",
        native_min_value=40,
        native_max_value=60,
        native_step=0.1,
        mode=NumberMode.BOX,
        write_key="genOffVolt",
    ),
    SunsynkNumberEntityDescription(
        key="gen_on_volt",
        name="Generator ON Voltage",
        native_unit_of_measurement="V",
        native_min_value=40,
        native_max_value=60,
        native_step=0.1,
        mode=NumberMode.BOX,
        write_key="genOnVolt",
    ),
    SunsynkNumberEntityDescription(
        key="ac_couple_freq_upper",
        name="AC Couple Upper Frequency",
        native_unit_of_measurement="Hz",
        native_min_value=50,
        native_max_value=65,
        native_step=0.1,
        mode=NumberMode.BOX,
        write_key="acCoupleFreqUpper",
    ),
    SunsynkNumberEntityDescription(
        key="grid_peak_power",
        name="Grid Peak-Shaving Power",
        native_unit_of_measurement="W",
        native_min_value=0,
        native_max_value=30000,
        native_step=100,
        mode=NumberMode.BOX,
        write_key="gridPeakPower",
    ),
)


class SunsynkGeneratorNumber(CoordinatorEntity[SunsynkCoordinator], NumberEntity):
    """Number entity for generator/AUX parameters — Tier 3 (confirmation required)."""

    entity_description: SunsynkNumberEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: SunsynkCoordinator,
        description: SunsynkNumberEntityDescription,
    ) -> None:
        """Initialize the generator number entity."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_device_info = coordinator.device_info
        self._attr_unique_id = f"sunsynk_{description.key}"
        self._optimistic_value: float | None = None

    @property
    def native_value(self) -> float | None:
        """Return the current value from inverter settings."""
        if self._optimistic_value is not None:
            return self._optimistic_value
        if self.coordinator.data is None:
            return None
        settings = self.coordinator.data.settings
        if not settings:
            return None
        val = settings.get(self.entity_description.write_key)
        if val is None:
            return None
        try:
            return float(val)
        except (ValueError, TypeError):
            return None

    async def async_set_native_value(self, value: float) -> None:
        """Set the value — requires Tier 3 confirmation."""
        self._optimistic_value = value
        self.async_write_ha_state()
        try:
            await self.coordinator.write_service.execute_write(
                self.entity_description.write_key,
                value,
            )
        except Exception:
            self._optimistic_value = None
            self.async_write_ha_state()
            raise
        finally:
            self._optimistic_value = None
        await self.coordinator.async_request_refresh()
