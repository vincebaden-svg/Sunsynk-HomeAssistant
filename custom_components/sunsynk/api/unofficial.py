"""Unofficial Sunsynk API client using direct HTTP calls to api.sunsynk.net."""
from __future__ import annotations

from datetime import date, datetime, timedelta
import json
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
                generator_power=float(flow_data.get("genPower", 0) or 0) or None,
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
        """Write a setting to the inverter via POST /api/v1/common/setting/{sn}/set."""
        if not self._access_token:
            await self.authenticate()

        sn = self._inverter_sn
        session = self._get_session()
        url = f"{self._base_url}/api/v1/common/setting/{sn}/set"

        # Build the payload
        payload: dict[str, Any] = {"sn": sn}

        # Map high-level keys to Sunsynk API field names
        key_mapping = {
            "work_mode": "sysWorkMode",
            "battery_priority": "energyMode",
            "grid_charge": "gridCharge",
            "solar_sell": "solarSell",
        }
        api_key = key_mapping.get(key, key)

        # Value mapping for battery_priority
        if key == "battery_priority":
            priority_map = {"battery": "0", "load": "1"}
            value = priority_map.get(str(value), str(value))

        # Convert values to the format the API expects
        if isinstance(value, bool):
            if api_key in (
                "time1on", "time2on", "time3on", "time4on", "time5on", "time6on",
                "genTime1on", "genTime2on", "genTime3on", "genTime4on",
                "genTime5on", "genTime6on",
                "mondayOn", "tuesdayOn", "wednesdayOn", "thursdayOn",
                "fridayOn", "saturdayOn", "sundayOn",
            ):
                payload[api_key] = value
            else:
                payload[api_key] = "1" if value else "0"
        elif isinstance(value, (int, float)):
            payload[api_key] = str(int(value)) if value == int(value) else str(value)
        else:
            payload[api_key] = str(value)

        # Work mode mapping
        if api_key == "sysWorkMode":
            mode_map = {
                "self_use": "1",
                "time_of_use": "2",
                "backup": "3",
                "peak_shaving": "4",
            }
            payload[api_key] = mode_map.get(str(value), str(value))

        headers = self._auth_headers()
        headers["Content-Type"] = "application/json"

        body = json.dumps(payload)

        _LOGGER.debug("Writing setting to %s: %s", url, payload)

        async with session.post(url, headers=headers, data=body) as resp:
            if resp.status == 401:
                raise SunsynkAuthError("Token expired during write")
            if resp.status != 200:
                resp_text = await resp.text()
                raise SunsynkCommunicationError(
                    f"Write failed: HTTP {resp.status} — {resp_text[:200]}"
                )
            data = await resp.json()
            if not data.get("success", False):
                raise SunsynkCommunicationError(
                    f"Write rejected by API: {data.get('msg', 'Unknown error')}"
                )

        _LOGGER.info(
            "Successfully wrote %s=%s to inverter %s",
            api_key, payload[api_key], sn
        )

    async def close(self) -> None:
        """Close the aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()
