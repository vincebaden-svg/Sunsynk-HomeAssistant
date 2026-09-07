"""Tests for the SunsynkCoordinator."""
from __future__ import annotations

from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.sunsynk.api.base import SunsynkData
from custom_components.sunsynk.api.exceptions import (
    SunsynkAuthError,
    SunsynkCommunicationError,
)
from custom_components.sunsynk.coordinator import SunsynkCoordinator


@pytest.fixture
def mock_client():
    """Create a mock API client."""
    client = MagicMock()
    client.fetch_all = AsyncMock(return_value=SunsynkData(
        pv_power=1500.0,
        battery_soc=85.0,
        grid_connected=True,
        inverter_sn="TEST123456",
    ))
    client.authenticate = AsyncMock()
    return client


@pytest.fixture
def coordinator(hass, mock_client):
    """Create a test coordinator."""
    return SunsynkCoordinator(
        hass=hass,
        client=mock_client,
        update_interval=timedelta(minutes=5),
        inverter_sn="TEST123456",
    )


async def test_successful_update(coordinator, mock_client):
    """Test coordinator returns data on successful poll."""
    data = await coordinator._async_update_data()
    assert data.pv_power == 1500.0
    assert data.battery_soc == 85.0
    assert coordinator._last_valid_data is not None


async def test_retains_last_valid_data_on_communication_error(coordinator, mock_client):
    """Test coordinator retains last valid data on network error."""
    # First successful poll
    await coordinator._async_update_data()

    # Second poll fails
    mock_client.fetch_all.side_effect = SunsynkCommunicationError("Network timeout")
    data = await coordinator._async_update_data()

    # Should return last valid data
    assert data.pv_power == 1500.0


async def test_reauthenticates_on_auth_error(coordinator, mock_client):
    """Test coordinator re-authenticates on 401."""
    # First successful poll to set last_valid_data
    await coordinator._async_update_data()

    # Next poll gets auth error, then succeeds after re-auth
    mock_client.fetch_all.side_effect = [
        SunsynkAuthError("Token expired"),
        SunsynkData(pv_power=2000.0, battery_soc=90.0, inverter_sn="TEST123456"),
    ]
    data = await coordinator._async_update_data()

    mock_client.authenticate.assert_called()
    assert data.pv_power == 2000.0
