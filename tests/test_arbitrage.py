"""The full arbitrage calculation, checked against one trade worked out by hand.

The trade: 1,000,000 barrels of WTI, Corpus Christi to Sikka on a Suezmax via
the Cape, with the sea distance fixed at 9,360 nm (see conftest.py).

It relies on these values in the YAML files (the test will flag it if they change):
  Suezmax 13 / 12.5 knots, 44 / 35 / 12 / 71 t per day; 2 days at each port;
  port costs $78,000 + $150,000; insurance on 110% of value; 360-day interest year;
  quality rule $0.40 per API degree and $1.00 per sulphur point.
"""

import pytest

from engine import arbitrage


def hand_inputs(**changes):
    base = dict(
        origin_key="corpus_christi", destination_key="sikka", vessel_key="suezmax", via="cape",
        cargo_bbl=1_000_000, grade="wti", destination_benchmark="brent",
        origin_benchmark_price=80.0, destination_benchmark_price=90.0,
        origin_differential=1.0, destination_differential=0.0,
        hire_usd_per_day=50_000, bunker_usd_per_tonne=600,
        charge_ballast_leg=True, include_war_risk=True,
        interest_rate_pct=6.0, financing_extra_days=0,
        insurance_rate_pct=0.05, transit_loss_pct=0.2, delay_days=0,
    )
    base.update(changes)
    return arbitrage.ArbInputs(**base)


def test_full_trade_by_hand(fixed_distance):
    r = arbitrage.run(hand_inputs())

    # Buy: WTI $80.00 + $1.00 Gulf Coast differential = $81.00.
    assert r.purchase_price == pytest.approx(81.00)
    # Sell: Brent $90.00 + quality $0.65 (WTI is slightly lighter and sweeter) = $90.65.
    assert r.quality_differential == pytest.approx(0.65)
    assert r.sale_value == pytest.approx(90.65)

    # Freight: the Cape voyage from test_voyage.py, $5,034,800 = $5.0348 a barrel.
    assert r.cost_stack["Freight"] == pytest.approx(5.0348)
    # Financing: $81m at 6% for 34 days (2 load + 30 at sea + 2 discharge):
    #   81,000,000 x 0.06 x 34 / 360 = $459,000 = $0.459 a barrel.
    assert r.cost_stack["Financing"] == pytest.approx(0.459)
    # Insurance: (81,000,000 + 5,034,800) x 110% x 0.05% = $47,319.14 = $0.0473 a barrel.
    assert r.cost_stack["Insurance"] == pytest.approx(0.04731914)
    # Transit loss: 0.2% of the $90.65 sale value = $0.1813 a barrel.
    assert r.cost_stack["Transit loss"] == pytest.approx(0.1813)
    assert r.cost_stack["Demurrage"] == 0

    # Landed cost: 81.00 + 5.0348 + 0.459 + 0.0473 + 0.1813 = $86.7224.
    assert r.landed_cost == pytest.approx(86.72241914)
    # Margin: 90.65 - 86.7224 = $3.9276 a barrel, $3.93m on the cargo. Arb open.
    assert r.margin_per_bbl == pytest.approx(3.92758086)
    assert r.margin_total_usd == pytest.approx(3_927_580.86)
    assert r.is_open
    assert r.benchmark_spread == pytest.approx(10.0)


def test_delay_adds_demurrage_and_interest(fixed_distance):
    r = arbitrage.run(hand_inputs(delay_days=3))
    # Demurrage: 3 x (50,000 + 7.5 t x $600) = $163,500 = $0.1635 a barrel.
    assert r.cost_stack["Demurrage"] == pytest.approx(0.1635)
    # Financing now runs 37 days: 81,000,000 x 0.06 x 37 / 360 = $499,500.
    assert r.cost_stack["Financing"] == pytest.approx(0.4995)


def test_narrow_spread_closes_the_arb(fixed_distance):
    # With Brent only $3 above WTI, the $5-plus freight alone wipes out the trade.
    r = arbitrage.run(hand_inputs(destination_benchmark_price=83.0))
    assert not r.is_open
    assert r.margin_per_bbl < 0


def test_default_inputs_come_from_the_yaml_files():
    inputs = arbitrage.default_inputs(80.0, 90.0, 600.0)
    assert inputs.vessel_key == "suezmax"
    assert inputs.cargo_bbl == 1_000_000
    assert inputs.origin_key == "corpus_christi" and inputs.destination_key == "sikka"
    assert inputs.interest_rate_pct > 0 and inputs.hire_usd_per_day > 0
