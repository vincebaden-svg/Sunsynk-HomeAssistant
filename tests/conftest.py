"""Test configuration for Sunsynk integration."""
from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import pytest

try:
    from pytest_homeassistant_custom_component.common import MockConfigEntry  # noqa: F401
    _HAS_HA_PYTEST = True
except ImportError:
    _HAS_HA_PYTEST = False


if not _HAS_HA_PYTEST:
    @pytest.fixture
    def hass(event_loop):
        """Provide a minimal HomeAssistant-like mock for coordinator tests."""
        mock_hass = MagicMock()
        mock_hass.loop = event_loop
        mock_hass.bus = MagicMock()
        mock_hass.bus.async_fire = MagicMock()
        mock_hass.data = {}
        return mock_hass
