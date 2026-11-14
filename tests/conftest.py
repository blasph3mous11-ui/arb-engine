"""Shared test set-up: a fixed sea distance, so results can be worked by hand."""

import pytest

from engine import voyage

HAND_DISTANCE_NM = 9360  # 30.0 days at 13 knots, 31.2 days at 12.5 knots


@pytest.fixture
def fixed_distance(monkeypatch):
    """Replace the routing library with a fixed 9,360 nm, whatever the route."""
    monkeypatch.setattr(voyage, "sea_route", lambda origin, destination, via: (HAND_DISTANCE_NM, ()))
    return HAND_DISTANCE_NM
