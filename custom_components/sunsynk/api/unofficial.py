"""Unofficial Sunsynk API client using sunsynk-api-client library."""
from __future__ import annotations

from datetime import datetime, timedelta
import logging
from typing import Any

from .base import SunsynkApiClient, SunsynkData
from .exceptions import SunsynkAuthError, SunsynkCommunicationError, SunsynkDataError

_LOGGER = logging.getLogger(__name__)

# Token lifetime is ~6 days; refresh at 80% = ~4.8 days
TOKEN_LIFETIME = timedelta(days=6)
TOKEN_REFRESH_THRESHOLD = TOKEN_LIFETIME * 0.8


class UnofficialApiClient(SunsynkApiClient):
    """API client using the unofficial Sunsynk Connect API.

    Wraps the sunsynk-api-client library which handles the 5-step RSA auth flow.
    Uses standard HTTPS (ssl=True) — no certificate issues on api.sunsynk.net.
    """

    def __init__(
        self,
        username: str,
        password: str,
        inverter_sn: str,
        region: str = "api.sunsynk.net",
    ) -> None:
        """Initialize the unofficial API client."""
        self._username = username
        self._password = password
        self._inverter_sn = inverter_sn
        self._region = region
        self._client = None
        self._authenticated_at: datetime | None = None

    async def authenticate(self) -> None:
        """Authenticate using username/password via sunsynk-api-client.

        The library handles the full 5-step RSA auth flow internally.
        Token is stored in memory by the library — never logged here.
        """
        try:
            from sunsynk.client import SunsynkClient  # type: ignore[import]

            base_url = f"https://{self._region}"
            self._client = SunsynkClient(
                self._username,
                self._password,
                base_url=base_url,
            )
            # Trigger authentication by making a test call
            await self._client.__aenter__()
            self._authenticated_at = datetime.now()
            _LOGGER.debug("Unofficial API authentication successful")
        except Exception as err:
            error_str = str(err).lower()
            if "401" in error_str or "unauthorized" in error_str or "auth" in error_str:
                raise SunsynkAuthError(f"Authentication failed: {err}") from err
            raise SunsynkCommunicationError(f"Connection error during auth: {err}") from err

    def _should_refresh_token(self) -> bool:
        """Check if token should be proactively refreshed."""
        if self._authenticated_at is None:
            return True
        age = datetime.now() - self._authenticated_at
        return age >= TOKEN_REFRESH_THRESHOLD

    async def fetch_all(self) -> SunsynkData:
        """Fetch all inverter data from the unofficial API."""
        if self._client is None:
            await self.authenticate()

        # Proactive token refresh
        if self._should_refresh_token():
            _LOGGER.debug("Proactively refreshing authentication token")
            await self.authenticate()

        try:
            inverters = await self._client.get_inverters()
            if not inverters:
                raise SunsynkDataError("No inverters found on account")

            # Find our inverter by serial number
            inverter = next(
                (inv for inv in inverters if inv.sn == self._inverter_sn),
                inverters[0],  # fallback to first if SN not matched
            )

            # Fetch realtime data
            grid = await self._client.get_inverter_realtime_grid(inverter.sn)
            battery = await self._client.get_inverter_realtime_battery(inverter.sn)
            solar_pv = await self._client.get_inverter_realtime_input(inverter.sn)
            output = await self._client.get_inverter_realtime_output(inverter.sn)

            return SunsynkData(
                pv_power=float(solar_pv.get_power()) if solar_pv else None,
                battery_power=float(battery.power) if battery else None,
                battery_soc=float(battery.soc) if battery else None,
                grid_power=float(grid.get_power()) if grid else None,
                load_power=float(output.get_power()) if output else None,
                grid_connected=grid is not None and grid.get_power() is not None,
                inverter_sn=inverter.sn,
            )

        except SunsynkAuthError:
            raise
        except SunsynkDataError:
            raise
        except Exception as err:
            error_str = str(err).lower()
            if "401" in error_str or "unauthorized" in error_str:
                raise SunsynkAuthError("Session expired") from err
            raise SunsynkCommunicationError(f"Failed to fetch data: {err}") from err

    async def write_setting(self, key: str, value: Any) -> None:
        """Write a setting to the inverter via the unofficial API."""
        if self._client is None:
            await self.authenticate()

        try:
            # Settings writes are handled via the client's update methods
            # Specific implementation depends on the setting key
            _LOGGER.debug(
                "Writing setting %s = %s to inverter %s", key, value, self._inverter_sn
            )
            # Full write implementation added in Epic 5
            raise NotImplementedError(f"Write for {key} not yet implemented")
        except NotImplementedError:
            raise
        except Exception as err:
            error_str = str(err).lower()
            if "401" in error_str or "unauthorized" in error_str:
                raise SunsynkAuthError("Session expired during write") from err
            raise SunsynkCommunicationError(f"Write failed: {err}") from err
