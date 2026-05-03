"""Tests for the official Sunsynk API client."""
from __future__ import annotations

import pytest

from custom_components.sunsynk.api.official import (
    OfficialApiClient,
    _compute_md5,
    _compute_hmac_sha256,
    _build_text_to_sign,
)


def test_compute_md5():
    """Test MD5 computation produces base64-encoded result."""
    result = _compute_md5('{"test": "data"}')
    assert isinstance(result, str)
    assert len(result) > 0


def test_compute_hmac_sha256():
    """Test HMAC-SHA256 produces base64-encoded result."""
    result = _compute_hmac_sha256("test text", "test secret")
    assert isinstance(result, str)
    assert len(result) > 0


def test_build_text_to_sign_structure():
    """Test textToSign is built in correct order per api-login.html spec."""
    text, sig_headers = _build_text_to_sign(
        method="POST",
        path="/oauth/token",
        body_md5="abc123==",
        app_key="204013305",
        nonce="test-nonce-uuid",
    )
    lines = text.split("\n")
    assert lines[0] == "POST"
    assert lines[1] == "application/json"   # accept
    assert lines[2] == "abc123=="           # Content-MD5
    assert lines[3] == "application/json"   # content-type
    assert lines[4] == ""                   # empty line
    assert "x-ca-key:204013305" in lines
    assert "x-ca-nonce:test-nonce-uuid" in lines
    assert lines[-1] == "/oauth/token"
    assert sig_headers == "x-ca-key,x-ca-nonce"


def test_client_initialization():
    """Test client initializes correctly."""
    client = OfficialApiClient(
        app_key="204013305",
        app_secret="zIQJeoPRXCjDV5anS5WIH7SQPAgdVaPm",
        inverter_sn="2207197610",
    )
    assert client._app_key == "204013305"
    assert client._access_token is None
