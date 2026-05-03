"""DataUpdateCoordinator for Sunsynk Solar Inverter."""
from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api.base import SunsynkApiClient, SunsynkData
from .api.exceptions import SunsynkApiError, SunsynkAuthError, SunsynkCommunicationError
from .const import DOMAIN
from .events import SunsynkEventDispatcher
from .services import WriteService
from .storage import SunsynkStorage

_LOGGER = logging.getLogger(__name__)


class SunsynkCoordinator(DataUpdateCoordinator[SunsynkData]):
    """Coordinator to manage Sunsynk inverter data updates.

    Polls the API at a configurable interval and provides data to all entity platforms.
    Handles authentication errors, network errors, and bad data gracefully.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        client: SunsynkApiClient,
        update_interval: timedelta,
        inverter_sn: str,
        soc_threshold: float = 20.0,
        solar_threshold: float = 500.0,
        summary_time: str = "18:00",
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
        )
        self._client = client
        self._inverter_sn = inverter_sn
        self._last_valid_data: SunsynkData | None = None
        self._dispatcher = SunsynkEventDispatcher(
            hass=hass,
            inverter_sn=inverter_sn,
            soc_threshold=soc_threshold,
            solar_threshold=solar_threshold,
            summary_time=summary_time,
        )
        self.write_service = WriteService(
            hass=hass,
            client=client,
            inverter_sn=inverter_sn,
        )
        self._storage: SunsynkStorage | None = None

    async def async_init_storage(self, db_path: str, retention_days: int = 30) -> None:
        """Initialize the time-series storage."""
        self._storage = SunsynkStorage(db_path=db_path, retention_days=retention_days)
        await self._storage.async_init()

    async def _async_update_data(self) -> SunsynkData:
        """Fetch data from the Sunsynk API.

        This method is called by DataUpdateCoordinator on each poll interval.
        It MUST NOT raise unhandled exceptions — errors are caught and logged.

        Returns:
            SunsynkData with current inverter readings, or last valid data on error.

        Raises:
            UpdateFailed: Only when no data has ever been fetched (first poll failure).
        """
        try:
            data = await self._client.fetch_all()
            self._last_valid_data = data
            self._dispatcher.dispatch(data)
            if self._storage is not None:
                try:
                    await self._storage.async_store(data)
                except Exception as store_err:  # noqa: BLE001
                    _LOGGER.warning("Failed to store reading: %s", store_err)
            return data

        except SunsynkAuthError as err:
            _LOGGER.warning(
                "Authentication error fetching Sunsynk data, re-authenticating: %s", err
            )
            try:
                await self._client.authenticate()
                data = await self._client.fetch_all()
                self._last_valid_data = data
                self._dispatcher.dispatch(data)
                return data
            except SunsynkAuthError as retry_err:
                _LOGGER.error("Re-authentication failed: %s", retry_err)
                if self._last_valid_data is not None:
                    return self._last_valid_data
                raise UpdateFailed(f"Authentication failed: {retry_err}") from retry_err

        except SunsynkCommunicationError as err:
            _LOGGER.warning(
                "Communication error fetching Sunsynk data (will retry next interval): %s",
                err,
            )
            if self._last_valid_data is not None:
                return self._last_valid_data
            raise UpdateFailed(f"Communication error: {err}") from err

        except SunsynkApiError as err:
            _LOGGER.warning(
                "API error fetching Sunsynk data (will retry next interval): %s", err
            )
            if self._last_valid_data is not None:
                return self._last_valid_data
            raise UpdateFailed(f"API error: {err}") from err

        except Exception as err:  # noqa: BLE001
            _LOGGER.error(
                "Unexpected error fetching Sunsynk data: %s", err, exc_info=True
            )
            if self._last_valid_data is not None:
                return self._last_valid_data
            raise UpdateFailed(f"Unexpected error: {err}") from err
