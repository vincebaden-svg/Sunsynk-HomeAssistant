"""Tests for the unofficial Sunsynk API client."""
from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.sunsynk.api.unofficial import UnofficialApiClient
from custom_components.sunsynk.api.exceptions import SunsynkAuthError, SunsynkCommunicationError


@pytest.fixture
def client():
    """Create a test client instance."""
    return UnofficialApiClient(
        username="test@example.com",
        password="testpassword",
        inverter_sn="TEST123456",
    )


def test_client_initialization(client):
    """Test client initializes with correct attributes."""
    assert client._username == "test@example.com"
    assert client._inverter_sn == "TEST123456"
    assert client._client is None
    assert client._authenticated_at is None


def test_should_refresh_token_when_not_authenticated(client):
    """Token refresh needed when never authenticated."""
    assert client._should_refresh_token() is True


def test_should_not_refresh_token_when_fresh(client):
    """Token refresh not needed when recently authenticated."""
    client._authenticated_at = datetime.now()
    assert client._should_refresh_token() is False
