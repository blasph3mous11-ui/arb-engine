"""The downloadable trade recap must say exactly what the calculation says."""

import pytest

from engine import arbitrage
from engine.recap import DISCLAIMER, trade_recap
from tests.test_arbitrage import hand_inputs

CONTEXT = {"origin_price_label": "WTI benchmark price, 17 Nov 2026 (US EIA)",
           "destination_price_label": "Brent benchmark price, 17 Nov 2026 (US EIA)",
           "freight_label": "Daily hire rate: test market", "hire_is_estimate": True,
           "made_on": "19 Nov 2026"}


def lookup(rows, item):
    return next(row for row in rows if row["Item"] == item)


def test_recap_of_the_hand_worked_trade(fixed_distance):
    result = arbitrage.run(hand_inputs())
    rows = trade_recap(result, CONTEXT)
    # The hand-worked margin, $3.9276 a barrel, and the numbers that make it up.
    assert lookup(rows, "Margin")["Value"] == pytest.approx(3.9276, abs=1e-4)
    assert lookup(rows, "Purchase price")["Value"] == pytest.approx(81.00)
    assert lookup(rows, "Sale value")["Value"] == pytest.approx(90.65)
    assert lookup(rows, "Freight")["Value"] == pytest.approx(5.0348)
    assert lookup(rows, "Verdict")["Value"] == "ARB OPEN"
    # Purchase price plus every cost line is the landed cost.
    costs = sum(row["Value"] for row in rows if row["Section"] == "Costs")
    assert lookup(rows, "Landed cost")["Value"] == pytest.approx(81.00 + costs, abs=1e-3)
    # The freight breakdown adds up to the freight line.
    breakdown = sum(row["Value"] for row in rows if row["Section"] == "Freight breakdown")
    assert breakdown == pytest.approx(lookup(rows, "Freight")["Value"], abs=1e-3)


def test_recap_marks_every_line(fixed_distance):
    rows = trade_recap(arbitrage.run(hand_inputs()), CONTEXT)
    for row in rows:
        if row["Section"] in ("Costs", "Freight breakdown"):
            assert row["Basis"] == "estimated", row
    assert lookup(rows, CONTEXT["origin_price_label"])["Basis"] == "published"
    assert lookup(rows, "What this is")["Value"] == DISCLAIMER
    assert "does not use traded freight rates or physical premium data" in DISCLAIMER


def test_recap_with_a_quote_and_set_speeds(fixed_distance):
    inputs = hand_inputs(freight_override_usd=5_000_000, speed_mode="custom",
                         laden_speed_knots=12, ballast_speed_knots=12)
    rows = trade_recap(arbitrage.run(inputs), {**CONTEXT, "freight_label": "Broker quote: lump sum"})
    assert lookup(rows, "Broker's quote for the cargo") == {
        "Section": "Freight breakdown", "Item": "Broker's quote for the cargo", "Value": 5_000_000.0,
        "Unit": "USD", "Basis": "typed in"}
    assert lookup(rows, "Speed loaded")["Value"] == 12 and lookup(rows, "Speed loaded")["Basis"] == "typed in"
    # 9,360 nm at 12 knots is 32.5 days, plus 2 days loading and 2 discharging.
    assert lookup(rows, "Days loaded")["Value"] == pytest.approx(36.5)
