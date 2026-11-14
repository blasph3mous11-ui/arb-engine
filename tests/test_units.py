"""Unit conversions, each checked against a sum done by hand."""

import pytest

from engine import units


def test_sailing_days():
    # 3,120 nautical miles at 13 knots: 13 x 24 = 312 nm a day, so 10 days.
    assert units.sailing_days(3120, 13) == pytest.approx(10.0)


def test_water_has_api_gravity_ten():
    # API 10 is defined as the density of water: 141.5 / (10 + 131.5) = 1.0.
    assert units.specific_gravity(10) == pytest.approx(1.0)
    # One tonne of water is one cubic metre, which is 6.2898 barrels.
    assert units.barrels_per_tonne(10) == pytest.approx(6.2898)


def test_wti_barrels_per_tonne():
    # WTI at 39.6 API: 141.5 / 171.1 = 0.82700; 6.2898 / 0.82700 = 7.6055 bbl per tonne.
    assert units.barrels_per_tonne(39.6) == pytest.approx(7.6055, abs=0.001)


def test_million_barrels_of_wti_in_tonnes():
    # 1,000,000 bbl / 7.6055 bbl per tonne = about 131,480 tonnes: fits a 158,000 t Suezmax.
    tonnes = units.barrels_to_tonnes(1_000_000, 39.6)
    assert tonnes == pytest.approx(131_480, rel=0.001)
    assert units.tonnes_to_barrels(tonnes, 39.6) == pytest.approx(1_000_000)


def test_dollars_per_tonne_to_per_barrel():
    # $76.055 a tonne / 7.6055 bbl per tonne = $10.00 a barrel.
    assert units.usd_per_tonne_to_usd_per_barrel(76.055, 39.6) == pytest.approx(10.0, abs=0.01)
