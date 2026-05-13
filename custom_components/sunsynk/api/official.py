"""Official Sunsynk OpenAPI client with dual-strategy data fetching.

Strategy 1 (hybrid): Official HMAC auth + unofficial API data endpoints with Bearer.
Strategy 2 (pure official): HMAC-signed GET requests to openapi.sunsynk.net.

The client tries the hybrid approach first. If the unofficial data endpoints reject
the official token (401), it falls back to HMAC-signed GET requests on the official API.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
from datetime import date, datetime, timedelta
from typing import Any
import uuid

import aiohttp

from .base import SunsynkApiClient, SunsynkData
from .exceptions import SunsynkAuthError, SunsynkCommunicationError, SunsynkDataError

_LOGGER = logging.getLogger(__name__)

OFFICIAL_API_BASE = "https://openapi.sunsynk.net"
UNOFFICIAL_API_BASE = "https://api.sunsynk.net"

TOKEN_LIFETIME = timedelta(days=6)
TOKEN_REFRESH_THRESHOLD = TOKEN_LIFETIME * 0.8


def _compute_md5(data: str) -> str:
    """Compute base64-encoded MD5 of a string."""
    md5_hash = hashlib.md5(data.encode()).digest()
    return base64.b64encode(md5_hash).decode()


def _compute_hmac_sha256(text: str, secret: str) -> str:
    """Compute base64-encoded HMAC-SHA256 signature."""
    sig = hmac.new(secret.encode(), text.encode(), hashlib.sha256).digest()
    return base64.b64encode(sig).decode()


def _build_url_to_sign(path: str, query_params: dict[str, str] | None = None) -> str:
    """Build the URL portion of textToSign with sorted query parameters.

    Per api-login.html urlToSign(): query params are sorted by key and appended.
    """
    if not query_params:
        return path
    sorted_params = sorted(query_params.items())
    qs = "&".join(f"{k}={v}" for k, v in sorted_params)
    return f"{path}?{qs}"


def _build_text_to_sign(
    method: str,
    path: str,
    body_md5: str,
    app_key: str,
    nonce: str,
    content_type: str = "application/json",
    query_params: dict[str, str] | None = None,
) -> tuple[str, str]:
    """Build the textToSign string and signatureHeaders per Sunsynk OpenAPI spec.

    For POST: content_type = "application/json", body_md5 = base64(md5(body))
    For GET:  content_type = "" (no body), body_md5 = "" (no body)

    Returns:
        Tuple of (textToSign, signatureHeaders)
    """
    # Headers to sign (sorted alphabetically, only x-ca-key and x-ca-nonce)
    headers_to_sign = {
        "x-ca-key": app_key,
        "x-ca-nonce": nonce,
    }
    sorted_keys = sorted(headers_to_sign.keys())
    signature_headers = ",".join(sorted_keys)

    # Build the URL portion with sorted query params
    url_to_sign = _build_url_to_sign(path, query_params)

    # Build textToSign in exact order per api-login.html reference
    lines = [
        method.upper(),
        "application/json",   # accept (always present)
        body_md5,             # Content-MD5 (empty string for GET)
        content_type,         # content-type (empty string for GET)
        "",                   # empty line (Date header placeholder)
    ]
    for key in sorted_keys:
        lines.append(f"{key}:{headers_to_sign[key]}")
    lines.append(url_to_sign)

    text_to_sign = "\n".join(lines)
    return text_to_sign, signature_headers


class OfficialApiClient(SunsynkApiClient):
    """Dual-strategy API client for Sunsynk.

    Strategy 1 (hybrid): HMAC auth on official API + Bearer data on unofficial API.
    Strategy 2 (pure): HMAC-signed requests for everything on official API.

    On first data fetch, tries hybrid. If unofficial rejects the token, switches
    to pure official with HMAC-signed GET requests.
    """

    def __init__(
        self,
        app_key: str,
        app_secret: str,
        inverter_sn: str,
        username: str = "",
        password: str = "",
    ) -> None:
        """Initialize the API client."""
        self._app_key = app_key
        self._app_secret = app_secret
        self._inverter_sn = inverter_sn
        self._username = username
        self._password = password
        self._access_token: str | None = None
        self._authenticated_at: datetime | None = None
        self._session: aiohttp.ClientSession | None = None
        self._plant_id: str | None = None
        # Strategy selection: None = not yet determined, True = hybrid, False = pure
        self._use_hybrid: bool | None = None

    def _get_session(self) -> aiohttp.ClientSession:
        """Get or create a standard HTTPS session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    def _should_refresh_token(self) -> bool:
        """Check if token should be proactively refreshed."""
        if self._authenticated_at is None:
            return True
        age = datetime.now() - self._authenticated_at
        return age >= TOKEN_REFRESH_THRESHOLD

    def _build_signed_headers_post(self, path: str, body: str) -> dict[str, str]:
        """Build HMAC-SHA256 signed headers for a POST request (auth)."""
        nonce = str(uuid.uuid4())
        body_md5 = _compute_md5(body) if body else ""

        text_to_sign, signature_headers = _build_text_to_sign(
            method="POST",
            path=path,
            body_md5=body_md5,
            app_key=self._app_key,
            nonce=nonce,
            content_type="application/json",
        )
        signature = _compute_hmac_sha256(text_to_sign, self._app_secret)

        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Content-MD5": body_md5,
            "X-Ca-Key": self._app_key,
            "X-Ca-Nonce": nonce,
            "X-Ca-Signature": signature,
            "X-Ca-Signature-Headers": signature_headers,
        }

    def _build_signed_headers_get(
        self, path: str, query_params: dict[str, str] | None = None
    ) -> dict[str, str]:
        """Build HMAC-SHA256 signed headers for a GET request (data).

        Key differences from POST signing:
        - No body → Content-MD5 is empty string
        - No body → content-type line is empty string in textToSign
        - Query params are sorted and included in the URL portion of the signature
        - Bearer token is included alongside HMAC headers
        """
        nonce = str(uuid.uuid4())

        text_to_sign, signature_headers = _build_text_to_sign(
            method="GET",
            path=path,
            body_md5="",
            app_key=self._app_key,
            nonce=nonce,
            content_type="",  # No content-type for GET (no body)
            query_params=query_params,
        )
        signature = _compute_hmac_sha256(text_to_sign, self._app_secret)

        headers = {
            "Accept": "application/json",
            "X-Ca-Key": self._app_key,
            "X-Ca-Nonce": nonce,
            "X-Ca-Signature": signature,
            "X-Ca-Signature-Headers": signature_headers,
        }
        # Include Bearer token if we have one (some endpoints may need both)
        if self._access_token:
            headers["Authorization"] = f"Bearer {self._access_token}"
        return headers

    def _bearer_headers(self) -> dict[str, str]:
        """Return Bearer token headers for unofficial API data requests."""
        return {
            "Authorization": f"Bearer {self._access_token}",
            "Accept": "application/json",
        }

    async def authenticate(self) -> None:
        """Authenticate via official API using HMAC-SHA256 signed POST."""
        path = "/oauth/token"
        body_data = {
            "username": self._username,
            "password": self._password,
            "grant_type": "password",
            "client_id": "openapi",
        }
        body = json.dumps(body_data, separators=(",", ":"), sort_keys=False)
        headers = self._build_signed_headers_post(path, body)

        session = self._get_session()
        try:
            async with session.post(
                f"{OFFICIAL_API_BASE}{path}",
                headers=headers,
                data=body,
            ) as resp:
                _LOGGER.debug(
                    "Official API auth response: status=%s url=%s",
                    resp.status, resp.url
                )
                if resp.status in (401, 403):
                    raise SunsynkAuthError(
                        f"Official API authentication failed: HTTP {resp.status}"
                    )
                if resp.status == 404:
                    raise SunsynkCommunicationError(
                        f"Official API endpoint not found (404): {resp.url}. "
                        "Check that openapi.sunsynk.net is accessible."
                    )
                resp.raise_for_status()
                data = await resp.json()

                if not data.get("success"):
                    raise SunsynkAuthError(
                        f"Official API auth error: {data.get('msg', 'Unknown error')}"
                    )

                token_data = data.get("data", {})
                self._access_token = token_data.get("access_token")
                if not self._access_token:
                    raise SunsynkAuthError("No access token in official API response")

                self._authenticated_at = datetime.now()
                _LOGGER.debug("Official API authentication successful")

        except SunsynkAuthError:
            raise
        except aiohttp.ClientError as err:
            raise SunsynkCommunicationError(
                f"Network error during official API auth: {err}"
            ) from err

    async def _ensure_authenticated(self) -> None:
        """Ensure we have a valid token, refreshing if needed."""
        if not self._access_token or self._should_refresh_token():
            _LOGGER.debug("Token missing or stale, re-authenticating")
            await self.authenticate()

    # ─── Hybrid strategy: unofficial data endpoints with Bearer token ───

    async def _hybrid_get_plant_id(self) -> str:
        """Get plant ID via unofficial API (hybrid strategy).

        Returns empty string if the unofficial API rejects the token (401).
        """
        session = self._get_session()
        url = f"{UNOFFICIAL_API_BASE}/api/v1/plants?page=1&limit=10&name=&status="

        async with session.get(url, headers=self._bearer_headers()) as resp:
            if resp.status == 401:
                return ""  # Signal that hybrid doesn't work
            resp.raise_for_status()
            data = await resp.json()

        plants = data.get("data", {}).get("infos", [])
        if not plants:
            raise SunsynkDataError(
                "No plants found on account. Check your Sunsynk credentials "
                "and ensure your inverter is registered."
            )
        return str(plants[0]["id"])

    async def _hybrid_fetch_all(self, plant_id: str) -> SunsynkData:
        """Fetch data via unofficial API endpoints with Bearer token.

        Calls multiple endpoints to populate all SunsynkData fields:
        - /plant/energy/{id}/flow — real-time power flow
        - /inverter/{sn}/realtime/input — PV input per string
        - /inverter/battery/{sn}/realtime — battery details
        - /inverter/grid/{sn}/realtime — grid details
        - /inverter/load/{sn}/realtime — load details
        """
        session = self._get_session()
        sn = self._inverter_sn
        headers = self._bearer_headers()
        today = date.today().isoformat()

        # Helper to GET with error handling
        async def _get_json(url: str) -> dict:
            async with session.get(url, headers=headers) as resp:
                if resp.status == 401:
                    raise SunsynkAuthError("Token expired during data fetch")
                resp.raise_for_status()
                result = await resp.json()
                return result.get("data", {}) if result.get("success", True) else {}

        # 1. Power flow (plant-level)
        flow_data = await _get_json(
            f"{UNOFFICIAL_API_BASE}/api/v1/plant/energy/{plant_id}/flow"
            f"?date={today}"
        )

        # 2. Battery realtime (inverter-level)
        battery_data = await _get_json(
            f"{UNOFFICIAL_API_BASE}/api/v1/inverter/battery/{sn}/realtime"
            f"?sn={sn}&lan=en"
        )

        # 3. Grid realtime (inverter-level)
        grid_data = await _get_json(
            f"{UNOFFICIAL_API_BASE}/api/v1/inverter/grid/{sn}/realtime"
            f"?sn={sn}"
        )

        # 4. Load realtime (inverter-level)
        load_data = await _get_json(
            f"{UNOFFICIAL_API_BASE}/api/v1/inverter/load/{sn}/realtime"
            f"?sn={sn}"
        )

        # 5. PV input (inverter-level)
        input_data = await _get_json(
            f"{UNOFFICIAL_API_BASE}/api/v1/inverter/{sn}/realtime/input"
        )

        # 6. Inverter settings (for writable entity state display)
        settings_data = await _get_json(
            f"{UNOFFICIAL_API_BASE}/api/v1/common/setting/{sn}/read"
        )

        return self._build_sunsynk_data(
            flow_data, battery_data, grid_data, load_data, input_data, settings_data
        )

    # ─── Pure official strategy: HMAC-signed GET requests ───

    async def _official_get(
        self, path: str, query_params: dict[str, str] | None = None
    ) -> dict:
        """Make an HMAC-signed GET request to the official API.

        Tries multiple signing variations if the first attempt returns 400,
        since the exact GET signing format is undocumented.
        """
        session = self._get_session()

        # Build full URL with sorted query params
        if query_params:
            sorted_params = sorted(query_params.items())
            qs = "&".join(f"{k}={v}" for k, v in sorted_params)
            url = f"{OFFICIAL_API_BASE}{path}?{qs}"
        else:
            url = f"{OFFICIAL_API_BASE}{path}"

        # Attempt 1: GET signing with empty content-type (most likely correct)
        headers = self._build_signed_headers_get(path, query_params)
        async with session.get(url, headers=headers) as resp:
            _LOGGER.debug("Official GET %s: status=%s", path, resp.status)
            if resp.status == 200:
                return await resp.json()
            if resp.status == 401:
                raise SunsynkAuthError(
                    f"Official API GET {path} returned 401 — token or signing invalid"
                )
            first_status = resp.status
            first_body = await resp.text()

        # Attempt 2: Try with content-type = "application/json" in signature
        # (some API gateways expect content-type even on GET)
        _LOGGER.debug(
            "Official GET %s returned %s, retrying with content-type in signature",
            path, first_status
        )
        nonce = str(uuid.uuid4())
        text_to_sign, signature_headers = _build_text_to_sign(
            method="GET",
            path=path,
            body_md5="",
            app_key=self._app_key,
            nonce=nonce,
            content_type="application/json",  # Include content-type this time
            query_params=query_params,
        )
        signature = _compute_hmac_sha256(text_to_sign, self._app_secret)
        headers_v2 = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-Ca-Key": self._app_key,
            "X-Ca-Nonce": nonce,
            "X-Ca-Signature": signature,
            "X-Ca-Signature-Headers": signature_headers,
        }
        if self._access_token:
            headers_v2["Authorization"] = f"Bearer {self._access_token}"

        async with session.get(url, headers=headers_v2) as resp:
            _LOGGER.debug("Official GET %s (v2): status=%s", path, resp.status)
            if resp.status == 200:
                return await resp.json()
            if resp.status == 401:
                raise SunsynkAuthError(
                    f"Official API GET {path} returned 401"
                )
            second_status = resp.status
            second_body = await resp.text()

        # Both attempts failed
        raise SunsynkCommunicationError(
            f"Official API GET {path} failed with both signing variants. "
            f"Attempt 1: HTTP {first_status} ({first_body[:100]}). "
            f"Attempt 2: HTTP {second_status} ({second_body[:100]}). "
            "The GET signing format may need further investigation."
        )

    async def _official_get_plant_id(self) -> str:
        """Get plant ID via official API with HMAC-signed GET."""
        # Try /plants (the path that returned 401, meaning it exists)
        query_params = {"page": "1", "limit": "10"}
        data = await self._official_get("/plants", query_params)

        if not data.get("success", True):
            raise SunsynkDataError(
                f"Official API /plants error: {data.get('msg', 'Unknown')}"
            )

        # Response structure may differ from unofficial API — try common shapes
        plants_data = data.get("data", {})
        if isinstance(plants_data, dict):
            plants = plants_data.get("infos", []) or plants_data.get("plants", [])
        elif isinstance(plants_data, list):
            plants = plants_data
        else:
            plants = []

        if not plants:
            raise SunsynkDataError(
                "No plants found via official API. Check your credentials "
                "and ensure your inverter is registered."
            )

        # Extract ID — try common field names
        plant = plants[0]
        plant_id = plant.get("id") or plant.get("plantId") or plant.get("plant_id")
        if not plant_id:
            raise SunsynkDataError(
                f"Could not extract plant ID from response: {plant}"
            )

        return str(plant_id)

    async def _official_fetch_all(self, plant_id: str) -> SunsynkData:
        """Fetch data via official API with HMAC-signed GET requests."""
        today = date.today().isoformat()
        sn = self._inverter_sn

        # Try power flow endpoint — official API may use different path prefixes
        flow_data: dict = {}
        for flow_path in [
            f"/plant/energy/{plant_id}/flow",
            f"/plant/{plant_id}/flow",
            f"/plants/{plant_id}/flow",
        ]:
            try:
                resp_data = await self._official_get(flow_path, {"date": today})
                flow_data = resp_data.get("data", {})
                _LOGGER.debug("Official flow endpoint found: %s", flow_path)
                break
            except SunsynkCommunicationError:
                continue
            except SunsynkAuthError:
                raise

        # Try battery endpoint
        battery_data: dict = {}
        for batt_path in [
            f"/inverter/battery/{sn}/realtime",
        ]:
            try:
                resp_data = await self._official_get(
                    batt_path, {"sn": sn, "lan": "en"}
                )
                battery_data = resp_data.get("data", {})
                break
            except SunsynkCommunicationError:
                continue
            except SunsynkAuthError:
                raise

        # Try grid endpoint
        grid_data: dict = {}
        for grid_path in [
            f"/inverter/grid/{sn}/realtime",
        ]:
            try:
                resp_data = await self._official_get(grid_path, {"sn": sn})
                grid_data = resp_data.get("data", {})
                break
            except SunsynkCommunicationError:
                continue
            except SunsynkAuthError:
                raise

        # Try load endpoint
        load_data: dict = {}
        for load_path in [
            f"/inverter/load/{sn}/realtime",
        ]:
            try:
                resp_data = await self._official_get(load_path, {"sn": sn})
                load_data = resp_data.get("data", {})
                break
            except SunsynkCommunicationError:
                continue
            except SunsynkAuthError:
                raise

        # Try input endpoint
        input_data: dict = {}
        for input_path in [
            f"/inverter/{sn}/realtime/input",
        ]:
            try:
                resp_data = await self._official_get(input_path)
                input_data = resp_data.get("data", {})
                break
            except SunsynkCommunicationError:
                continue
            except SunsynkAuthError:
                raise

        if not any([flow_data, battery_data, grid_data, load_data, input_data]):
            _LOGGER.warning(
                "No data retrieved from official API endpoints. "
                "Returning partial SunsynkData."
            )

        return self._build_sunsynk_data(
            flow_data, battery_data, grid_data, load_data, input_data, {}
        )

    # ─── Common helpers ───

    def _build_sunsynk_data(
        self,
        flow_data: dict,
        battery_data: dict,
        grid_data: dict,
        load_data: dict,
        input_data: dict,
        settings_data: dict | None = None,
    ) -> SunsynkData:
        """Build SunsynkData from multiple endpoint responses.

        Args:
            flow_data: /plant/energy/{id}/flow response
            battery_data: /inverter/battery/{sn}/realtime response
            grid_data: /inverter/grid/{sn}/realtime response
            load_data: /inverter/load/{sn}/realtime response
            input_data: /inverter/{sn}/realtime/input response
        """

        def _float(val: Any, default: float = 0.0) -> float:
            """Safely convert to float."""
            try:
                return float(val) if val is not None else default
            except (ValueError, TypeError):
                return default

        # PV power — from flow (plant total) or input (inverter pac)
        pv_power = _float(flow_data.get("pvPower")) or _float(input_data.get("pac"))

        # PV per-string power from input endpoint pvIV array
        pv_iv = input_data.get("pvIV", [])
        pv1_power = _float(pv_iv[0].get("ppv")) if len(pv_iv) > 0 else None
        pv2_power = _float(pv_iv[1].get("ppv")) if len(pv_iv) > 1 else None
        pv3_power = _float(pv_iv[2].get("ppv")) if len(pv_iv) > 2 else None
        pv4_power = _float(pv_iv[3].get("ppv")) if len(pv_iv) > 3 else None

        # Battery — prefer inverter-level data, fall back to flow
        battery_power = _float(battery_data.get("power")) or _float(
            flow_data.get("battPower")
        )
        battery_soc = _float(battery_data.get("soc")) or _float(
            flow_data.get("soc")
        )
        battery_voltage = _float(battery_data.get("voltage")) if battery_data.get("voltage") else None
        battery_current = _float(battery_data.get("current")) if battery_data.get("current") else None

        # Grid — prefer inverter-level
        grid_power = _float(grid_data.get("pac")) or _float(
            flow_data.get("gridOrMeterPower")
        )

        # Load — prefer inverter-level
        load_power = _float(load_data.get("totalPower")) or _float(
            flow_data.get("loadOrEpsPower")
        )

        # Grid connected — check grid frequency (< 40Hz = disconnected)
        grid_fac = _float(grid_data.get("fac"))
        if grid_fac > 0:
            grid_connected = grid_fac >= 40.0
        else:
            # Fall back to flow data flags
            grid_connected = (
                not bool(flow_data.get("existsGen", False))
                and bool(flow_data.get("gridTo", True))
            )

        # Energy today — from inverter-level endpoints
        pv_energy_today = _float(input_data.get("etoday"))
        battery_charge_today = _float(battery_data.get("etodayChg"))
        battery_discharge_today = _float(battery_data.get("etodayDischg"))
        grid_import_today = _float(grid_data.get("etodayFrom"))
        grid_export_today = _float(grid_data.get("etodayTo"))
        load_energy_today = _float(load_data.get("dailyUsed"))

        # System status from grid data
        grid_status = grid_data.get("status")
        system_status = (
            f"grid_status={grid_status}" if grid_status is not None else None
        )

        return SunsynkData(
            pv_power=pv_power,
            pv1_power=pv1_power,
            pv2_power=pv2_power,
            pv3_power=pv3_power,
            pv4_power=pv4_power,
            battery_power=battery_power,
            battery_soc=battery_soc,
            battery_voltage=battery_voltage,
            battery_current=battery_current,
            grid_power=grid_power,
            load_power=load_power,
            grid_connected=grid_connected,
            pv_energy_today=pv_energy_today,
            battery_charge_today=battery_charge_today,
            battery_discharge_today=battery_discharge_today,
            grid_import_today=grid_import_today,
            grid_export_today=grid_export_today,
            load_energy_today=load_energy_today,
            system_status=system_status,
            inverter_sn=self._inverter_sn,
            settings=settings_data or {},
        )

    # ─── Public interface ───

    async def _get_plant_id(self) -> str:
        """Get plant ID using the active strategy."""
        if self._plant_id:
            return self._plant_id

        if self._use_hybrid:
            self._plant_id = await self._hybrid_get_plant_id()
        else:
            self._plant_id = await self._official_get_plant_id()

        return self._plant_id

    async def fetch_all(self) -> SunsynkData:
        """Fetch inverter data using the best available strategy.

        First call determines strategy:
        1. Try hybrid (unofficial data endpoints with Bearer token)
        2. If rejected (401), fall back to pure official (HMAC-signed GET)
        """
        await self._ensure_authenticated()

        try:
            # Determine strategy on first call
            if self._use_hybrid is None:
                _LOGGER.debug("Determining data fetch strategy...")
                plant_id = await self._hybrid_get_plant_id()
                if plant_id:
                    self._use_hybrid = True
                    self._plant_id = plant_id
                    _LOGGER.info(
                        "Hybrid strategy active: official auth + unofficial data"
                    )
                else:
                    self._use_hybrid = False
                    _LOGGER.info(
                        "Hybrid rejected (401), using pure official API with "
                        "HMAC-signed GET requests"
                    )
                    self._plant_id = await self._official_get_plant_id()

            plant_id = await self._get_plant_id()

            if self._use_hybrid:
                return await self._hybrid_fetch_all(plant_id)
            else:
                return await self._official_fetch_all(plant_id)

        except SunsynkAuthError:
            raise
        except SunsynkDataError:
            raise
        except aiohttp.ClientError as err:
            raise SunsynkCommunicationError(
                f"Network error fetching data: {err}"
            ) from err
        except Exception as err:  # noqa: BLE001
            error_str = str(err).lower()
            if "401" in error_str or "unauthorized" in error_str:
                raise SunsynkAuthError("Session expired") from err
            raise SunsynkCommunicationError(
                f"Failed to fetch data: {err}"
            ) from err

    async def write_setting(self, key: str, value: Any) -> None:
        """Write a setting to the inverter via POST /api/v1/common/setting/{sn}/set.

        The Sunsynk API expects a JSON body with the inverter serial number
        and one or more setting key-value pairs. Boolean values must be sent
        as actual booleans, time values as strings like "06:00", and numeric
        values as strings.
        """
        await self._ensure_authenticated()

        sn = self._inverter_sn
        session = self._get_session()
        url = f"{UNOFFICIAL_API_BASE}/api/v1/common/setting/{sn}/set"

        # Build the payload — sn is always required
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
            # Some boolean fields use true/false, others use "1"/"0"
            if api_key in (
                "time1on", "time2on", "time3on", "time4on", "time5on", "time6on",
                "genTime1on", "genTime2on", "genTime3on", "genTime4on",
                "genTime5on", "genTime6on",
                "mondayOn", "tuesdayOn", "wednesdayOn", "thursdayOn",
                "fridayOn", "saturdayOn", "sundayOn",
            ):
                payload[api_key] = value
            else:
                # peakAndVallery, energyMode, solarSell, gridCharge use "1"/"0"
                payload[api_key] = "1" if value else "0"
        elif isinstance(value, (int, float)):
            payload[api_key] = str(int(value)) if value == int(value) else str(value)
        else:
            payload[api_key] = str(value)

        # Work mode mapping: our names → Sunsynk numeric codes
        if api_key == "sysWorkMode":
            mode_map = {
                "self_use": "1",
                "time_of_use": "2",
                "backup": "3",
                "peak_shaving": "4",
            }
            payload[api_key] = mode_map.get(str(value), str(value))

        headers = self._bearer_headers()
        headers["Content-Type"] = "application/json"

        body = json.dumps(payload)

        _LOGGER.debug(
            "Writing setting to %s: %s", url, payload
        )

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
