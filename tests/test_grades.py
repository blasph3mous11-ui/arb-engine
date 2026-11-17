"""More crude grades: quality value and purchase price for each."""

import pytest

from engine import arbitrage
from engine import assumptions as A
from tests.test_arbitrage import hand_inputs


def test_shipped_grades():
    assert arbitrage.shipped_grades("us_gulf") == ["wti", "wti_midland", "mars"]
    assert arbitrage.shipped_grades("north_sea") == ["forties", "johan_sverdrup"]
    assert len(arbitrage.shipped_grades()) == 5
    # Each North Sea blend loads at its own terminal; US grades load at any US Gulf port.
    assert arbitrage.shipped_grades(origin_key="hound_point") == ["forties"]
    assert arbitrage.shipped_grades(origin_key="mongstad") == ["johan_sverdrup"]
    assert arbitrage.shipped_grades(origin_key="houston") == ["wti", "wti_midland", "mars"]


def test_quality_by_hand_against_brent():
    # Brent is 38.3 API and 0.37% sulphur; the rule is $0.40 a degree and $1.00 a sulphur point.
    # WTI Midland (42.0, 0.20%): 3.7 x 0.40 = 1.48, plus 0.17 x 1.00 = 0.17 -> +$1.65.
    assert arbitrage.grade_quality_differential("wti_midland", "brent") == pytest.approx(1.65)
    # Mars (29.5, 1.89%): -8.8 x 0.40 = -3.52, minus 1.52 x 1.00 -> -$5.04.
    assert arbitrage.grade_quality_differential("mars", "brent") == pytest.approx(-5.04)


def test_quality_by_hand_against_dubai():
    # Dubai is 31.0 API and 2.0% sulphur. Mars: -1.5 x 0.40 = -0.60, plus 0.11 x 1.00 -> -$0.49.
    assert arbitrage.grade_quality_differential("mars", "dubai") == pytest.approx(-0.49)


def test_each_grade_has_its_own_differential():
    assert arbitrage.export_differential("wti") == A.get("costs", "pricing", "origin_differential_usd_per_bbl")
    assert arbitrage.export_differential("wti_midland") == 1.30
    assert arbitrage.export_differential("mars") == 1.50
    inputs = arbitrage.default_inputs(80.0, 90.0, 600.0, grade="mars")
    assert inputs.origin_differential == 1.50


def test_mars_cargo_by_hand(fixed_distance):
    # The hand-worked trade, shipping Mars instead of WTI: buy at 80 + 1.50 = $81.50;
    # sell at Brent 90 - 5.04 = $84.96. Freight is unchanged at $5.0348.
    r = arbitrage.run(hand_inputs(grade="mars", origin_differential=1.50))
    assert r.purchase_price == pytest.approx(81.50)
    assert r.sale_value == pytest.approx(84.96)
    assert r.cost_stack["Freight"] == pytest.approx(5.0348)
    assert not r.is_open


def test_heavier_grade_weighs_more_per_barrel():
    # Mars is denser than WTI, so a million barrels weigh more tonnes.
    assert arbitrage.cargo_tonnes(1_000_000, "mars") > arbitrage.cargo_tonnes(1_000_000, "wti")
