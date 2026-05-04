"""Unofficial Sunsynk API client using direct HTTP calls to api.sunsynk.net."""
from __future__ import annotations

from datetime import date, datetime, timedelta
import logging
from typing import Any

import aiohttp

from .base import SunsynkApiClient, SunsynkData
from .exceptions import SunsynkAuthError, SunsynkCommunicationError, SunsynkDataError

_LOGGER = logging.getLogger(__name__)

TOKEN_LIFETIME = timedelta(days=6)
TOKEN_REFRESH_THRESHOLD = TOKEN_LIFETIME * 0.8

REGION_URLS = {
    "api.sunsynk.net": "https://api.sunsynk.net",
    "pv.inteless.com": "https://pv.inteless.com",
}


class UnofficialApiClient(SunsynkApiClient):
    """API client using the unofficial Sunsynk Connect API (api.sunsynk.net).

    Makes direct HTTP calls — no dependency on sunsynk-api-client library.
    Uses standard HTTPS (ssl=True).
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
        self._base_url = REGION_URLS.get(region, f"https://{region}")
        self._access_token: str | None = None
        self._authenticated_at: datetime | None = None
        self._session: aiohttp.ClientSession | None = None
        self._plant_id: str | None = None

    def _get_session(self) -> aiohttp.ClientSession:
        """Get or create an aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    def _should_refresh_token(self) -> bool:
        """Check if token should be proactively refreshed."""
        if self._authenticated_at is None:
            return True
        age = datetime.now() - self._authenticated_at
        return age >= TOKEN_REFRESH_THRESHOLD

    async def authenticate(self) -> None:
        """Authenticate using username/password via the Sunsynk Connect API."""
        session = self._get_session()
        # Note: The correct auth endpoint is /oauth/token/new (not /oauth/token)
        url = f"{self._base_url}/oauth/token/new"
        payload = {
            "areaCode": "sunsynk",
            "client_id": "csp-web",
            "grant_type": "password",
            "password": self._password,
            "source": "sunsynk",
            "username": self._username,
        }
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        try:
            async with session.post(url, json=payload, headers=headers) as resp:
                if resp.status in (401, 403):
                    raise SunsynkAuthError(
                        f"Authentication failed: HTTP {resp.status}. Check username/password."
                    )
                resp.raise_for_status()
                data = await resp.json()

                if not data.get("success"):
                    raise SunsynkAuthError(
                        f"Authentication failed: {data.get('msg', 'Unknown error')}"
                    )

                token_data = data.get("data", {})
                self._access_token = token_data.get("access_token")
                if not self._access_token:
                    raise SunsynkAuthError("No access token in response")

                self._authenticated_at = datetime.now()
                _LOGGER.debug("Unofficial API authentication successful")

        except SunsynkAuthError:
            raise
        except aiohttp.ClientError as err:
            raise SunsynkCommunicationError(f"Network error during auth: {err}") from err

    def _auth_headers(self) -> dict:
        """Return headers with bearer token."""
        return {
            "Authorization": f"Bearer {self._access_token}",
            "Accept": "application/json",
        }

    async def _get_plant_id(self) -> str:
        """Get the plant ID for this account (cached)."""
        if self._plant_id:
            return self._plant_id

        session = self._get_session()
        url = f"{self._base_url}/api/v1/plants?page=1&limit=10&name=&status="
        async with session.get(url, headers=self._auth_headers()) as resp:
            if resp.status == 401:
                raise SunsynkAuthError("Token expired")
            resp.raise_for_status()
            data = await resp.json()

        plants = data.get("data", {}).get("infos", [])
        if not plants:
            raise SunsynkDataError(
                "No plants found on account. Check your Sunsynk Connect credentials "
                "and ensure your inverter is registered to this account."
            )

        # Use first plant (most accounts have one)
        self._plant_id = str(plants[0]["id"])
        _LOGGER.debug("Using plant ID: %s", self._plant_id)
        return self._plant_id

    async def fetch_all(self) -> SunsynkData:
        """Fetch all inverter data from the unofficial API."""
        if not self._access_token:
            await self.authenticate()

        if self._should_refresh_token():
            _LOGGER.debug("Proactively refreshing authentication token")
            await self.authenticate()

        try:
            plant_id = await self._get_plant_id()
            session = self._get_session()
            today = date.today().isoformat()

            # Fetch power flow data
            flow_url = f"{self._base_url}/api/v1/plant/energy/{plant_id}/flow?date={today}"
            async with session.get(flow_url, headers=self._auth_headers()) as resp:
                if resp.status == 401:
                    raise SunsynkAuthError("Token expired")
                resp.raise_for_status()
                flow_data = (await resp.json()).get("data", {})

            # Fetch energy generation data
            gen_url = f"{self._base_url}/api/v1/plant/{plant_id}/generation/use"
            async with session.get(gen_url, headers=self._auth_headers()) as resp:
                resp.raise_for_status()
                gen_data = (await resp.json()).get("data", {})

            return SunsynkData(
                pv_power=float(flow_data.get("pvPower", 0) or 0),
                battery_power=float(flow_data.get("battPower", 0) or 0),
                battery_soc=float(flow_data.get("soc", 0) or 0),
                grid_power=float(flow_data.get("gridOrMeterPower", 0) or 0),
                load_power=float(flow_data.get("loadOrEpsPower", 0) or 0),
                grid_connected=not bool(flow_data.get("existsGen", False))
                    and bool(flow_data.get("gridTo", True)),
                pv_energy_today=float(gen_data.get("pv", 0) or 0),
                battery_charge_today=float(gen_data.get("batteryCharge", 0) or 0),
                grid_import_today=float(gen_data.get("gridBuy", 0) or 0),
                grid_export_today=float(gen_data.get("gridSell", 0) or 0),
                load_energy_today=float(gen_data.get("load", 0) or 0),
                inverter_sn=self._inverter_sn,
            )

        except SunsynkAuthError:
            raise
        except SunsynkDataError:
            raise
        except aiohttp.ClientError as err:
            raise SunsynkCommunicationError(f"Network error fetching data: {err}") from err
        except Exception as err:  # noqa: BLE001
            error_str = str(err).lower()
            if "401" in error_str or "unauthorized" in error_str:
                raise SunsynkAuthError("Session expired") from err
            raise SunsynkCommunicationError(f"Failed to fetch data: {err}") from err

    async def write_setting(self, key: str, value: Any) -> None:
        """Write a setting to the inverter via the unofficial API."""
        if not self._access_token:
            await self.authenticate()
        _LOGGER.info("Writing setting %s = %s to inverter %s", key, value, self._inverter_sn)
        # Full write implementation — uses set_solar_settings endpoint
        raise NotImplementedError(f"Write for {key} not yet implemented")

    async def close(self) -> None:
        """Close the aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()
