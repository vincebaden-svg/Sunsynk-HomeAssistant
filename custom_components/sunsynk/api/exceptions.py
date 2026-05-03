"""Exceptions for the Sunsynk API client."""
from __future__ import annotations


class SunsynkApiError(Exception):
    """Base exception for all Sunsynk API errors."""


class SunsynkAuthError(SunsynkApiError):
    """Authentication failed — invalid credentials or expired token."""


class SunsynkCommunicationError(SunsynkApiError):
    """Network or communication error reaching the Sunsynk API."""


class SunsynkDataError(SunsynkApiError):
    """Unexpected or invalid data received from the Sunsynk API."""
