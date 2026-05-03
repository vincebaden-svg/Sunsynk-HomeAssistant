"""Official Sunsynk OpenAPI client using HMAC-SHA256 signing."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
from typing import Any
import uuid

import aiohttp

from .base import SunsynkApiClient, SunsynkData
from .exceptions import SunsynkAuthError, SunsynkCommunicationError

_LOGGER = logging.getLogger(__name__)

OFFICIAL_API_BASE = "http://openapi.sunsynk.net"


def _compute_md5(data: str) -> str:
    """Compute base64-encoded MD5 of a string."""
    md5 = hashlib.md5(data.encode()).digest()
    return base64.b64encode(md5).decode()


def _compute_hmac_sha256(text: str, secret: str) -> str:
    """Compute base64-encoded HMAC-SHA256 signature."""
    sig = hmac.new(secret.encode(), text.encode(), hashlib.sha256).digest()
    return base64.b64encode(sig).decode()


def _build_text_to_sign(
    method: str,
    path: str,
    body_md5: str,
    app_key: str,
    nonce: str,
) -> tuple[str, str]:
    """Build the textToSign string and signatureHeaders per Sunsynk OpenAPI spec.

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

    # Build textToSign in exact order per api-login.html
    lines = [
        method.upper(),
        "application/json",   # accept
        body_md5,             # Content-MD5
        "application/json",   # content-type
        "",                   # empty line (Date header placeholder)
    ]
    for key in sorted_keys:
        lines.append(f"{key}:{headers_to_sign[key]}")
    lines.append(path)

    text_to_sign = "\n".join(lines)
    return text_to_sign, signature_headers


class OfficialApiClient(SunsynkApiClient):
    """API client using the official Sunsynk OpenAPI with HMAC-SHA256 signing.

    SECURITY NOTE: ssl=False is required due to certificate issues on openapi.sunsynk.net.
    Users are warned about this during config flow setup.
    """

    def __init__(
        self,
        app_key: str,
        app_secret: str,
        inverter_sn: str,
    ) -> None:
        """Initialize the official API client."""
        self._app_key = app_key
        self._app_secret = app_secret
        self._inverter_sn = inverter_sn
        self._access_token: str | None = None
        self._session: aiohttp.ClientSession | None = None

    def _get_session(self) -> aiohttp.ClientSession:
        """Get or create an aiohttp session with SSL verification disabled."""
        if self._session is None or self._session.closed:
            # ssl=False required — openapi.sunsynk.net has certificate issues
            connector = aiohttp.TCPConnector(ssl=False)
            self._session = aiohttp.ClientSession(connector=connector)
        return self._session

    def _build_signed_headers(
        self, method: str, path: str, body: str
    ) -> dict[str, str]:
        """Build HMAC-SHA256 signed request headers."""
        nonce = str(uuid.uuid4())
        body_md5 = _compute_md5(body) if body else ""

        text_to_sign, signature_headers = _build_text_to_sign(
            method, path, body_md5, self._app_key, nonce
        )
        signature = _compute_hmac_sha256(text_to_sign, self._app_secret)

        return {
            "content-type": "application/json",
            "accept": "application/json",
            "Content-MD5": body_md5,
            "X-Ca-Key": self._app_key,
            "X-Ca-Nonce": nonce,
            "X-Ca-Signature": signature,
            "X-Ca-Signature-Headers": signature_headers,
        }

    async def authenticate(self) -> None:
        """Authenticate using appKey/appSecret with HMAC-SHA256 signing."""
        path = "/oauth/token"
        body_data = {
            "username": "",  # Not used for official API — key/secret auth
            "password": "",
            "grant_type": "password",
            "client_id": "openapi",
        }
        body = json.dumps(body_data)
        headers = self._build_signed_headers("POST", path, body)

        session = self._get_session()
        try:
            async with session.post(
                f"{OFFICIAL_API_BASE}{path}",
                headers=headers,
                data=body,
            ) as resp:
                if resp.status in (401, 403):
                    raise SunsynkAuthError(
                        f"Official API authentication failed: HTTP {resp.status}"
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

                _LOGGER.debug("Official API authentication successful")

        except SunsynkAuthError:
            raise
        except aiohttp.ClientError as err:
            raise SunsynkCommunicationError(
                f"Network error during official API auth: {err}"
            ) from err

    async def fetch_all(self) -> SunsynkData:
        """Fetch inverter data from the official API.

        NOTE: Official API endpoint paths require spike task verification.
        This implementation uses the same endpoint structure as the unofficial API
        as a starting point — update once official endpoints are confirmed.
        """
        if not self._access_token:
            await self.authenticate()

        # TODO: Replace with verified official API endpoints after spike task
        # For now, return minimal data to satisfy the interface
        _LOGGER.warning(
            "Official API data endpoints not yet verified — spike task required. "
            "Returning empty SunsynkData."
        )
        return SunsynkData(inverter_sn=self._inverter_sn)

    async def write_setting(self, key: str, value: Any) -> None:
        """Write a setting via the official API."""
        if not self._access_token:
            await self.authenticate()

        # Full implementation in Epic 5 after endpoint verification
        raise NotImplementedError(
            f"Official API write for {key} not yet implemented — spike task required"
        )

    async def close(self) -> None:
        """Close the aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()
