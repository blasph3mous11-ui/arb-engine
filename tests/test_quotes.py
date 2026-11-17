"""Broker freight quotes: Worldscale and lump sum, and the owner's implied daily earnings."""

import pytest

from engine import arbitrage, scenarios, voyage
from engine.voyage import estimate_voyage, implied_tce, worldscale_freight_usd
from tests.test_arbitrage import hand_inputs
from tests.test_voyage import COMMON


def test_worldscale_freight_by_hand():
    # WS 100 on a $20.00 a tonne flat rate, 131,480 tonnes: 1.00 x 20 x 131,480 = $2,629,600.
    assert worldscale_freight_usd(100, 20.0, 131_480) == pytest.approx(2_629_600)
    # WS 150 is one and a half times the flat rate: $3,944,400.
    assert worldscale_freight_usd(150, 20.0, 131_480) == pytest.approx(3_944_400)


def test_cargo_tonnes_for_a_million_barrels_of_wti():
    # 1,000,000 bbl / 7.6055 bbl per tonne = about 131,480 tonnes (see test_units.py).
    assert arbitrage.cargo_tonnes(1_000_000, "wti") == pytest.approx(131_480, rel=0.001)


def test_tce_gives_back_the_hire_rate_when_freight_is_built_from_it():
    v = estimate_voyage(via="cape", **COMMON)
    assert implied_tce(v, v.total_cost) == pytest.approx(50_000)


def test_tce_of_a_lump_sum_by_hand():
    # The hand-worked Cape voyage: 65.2 days; fuel $1,546,800 and ports $228,000 are paid
    # by the owner. A $6,000,000 lump sum leaves 6,000,000 - 1,774,800 = $4,225,200,
    # which over 65.2 days is $64,803.68 a day.
    v = estimate_voyage(via="cape", **COMMON)
    assert implied_tce(v, 6_000_000) == pytest.approx(4_225_200 / 65.2)


def test_quote_replaces_built_up_freight(fixed_distance):
    r = arbitrage.run(hand_inputs(freight_override_usd=6_000_000))
    # Freight is the quote: $6.00 a barrel on a million barrels.
    assert r.cost_stack["Freight"] == pytest.approx(6.0)
    # The hand-worked trade had freight $5.0348; the margin falls by the difference,
    # plus the insurance on the extra freight (x 110% x 0.05%).
    extra = 6.0 - 5.0348
    assert r.margin_per_bbl == pytest.approx(3.92758086 - extra * (1 + 1.10 * 0.0005))
    assert r.implied_tce == pytest.approx(4_225_200 / 65.2)


def test_without_a_quote_nothing_changes(fixed_distance):
    r = arbitrage.run(hand_inputs())
    assert r.margin_per_bbl == pytest.approx(3.92758086)
    assert r.implied_tce == pytest.approx(50_000)


def test_delay_with_a_quote_is_charged_at_the_quote_s_daily_earnings(fixed_distance):
    # 3 days late: 3 x (64,803.68 + 7.5 t x $600 idle fuel) = $207,911.04.
    r = arbitrage.run(hand_inputs(freight_override_usd=6_000_000, delay_days=3))
    assert r.cost_stack["Demurrage"] == pytest.approx(3 * (4_225_200 / 65.2 + 4_500) / 1_000_000)


def test_tornado_flexes_the_quote_in_quote_mode(fixed_distance):
    rows = {r["driver"].split(" (")[0]: r for r in scenarios.tornado(hand_inputs(freight_override_usd=6_000_000))}
    assert "Freight quote" in rows and "Vessel hire rate" not in rows
    # 25% of a $6.00 quote is $1.50 each way, plus insurance on it: swing $3.00 x (1 + 0.00055).
    assert rows["Freight quote"]["swing"] == pytest.approx(3.0 * (1 + 1.10 * 0.0005))
