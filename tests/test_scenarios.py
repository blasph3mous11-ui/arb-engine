"""Scenario tools: break-even, tornado and the historical re-run."""

import pandas as pd
import pytest

from engine import arbitrage, scenarios
from tests.test_arbitrage import hand_inputs


def test_breakeven_spread_gives_zero_margin(fixed_distance):
    inputs = hand_inputs()
    spread = scenarios.breakeven_spread(inputs)
    at_breakeven = inputs.with_changes(
        destination_benchmark_price=inputs.origin_benchmark_price + spread)
    assert arbitrage.run(at_breakeven).margin_per_bbl == pytest.approx(0, abs=1e-6)


def test_breakeven_spread_by_hand(fixed_distance):
    # In the hand-worked trade the margin is $3.9276 at a $10 spread. Each extra
    # dollar of destination price adds $1 less the 0.2% transit loss = $0.998.
    # So break-even is 10 - 3.92758086 / 0.998 = $6.0645.
    assert scenarios.breakeven_spread(hand_inputs()) == pytest.approx(10 - 3.92758086 / 0.998)


def test_tornado_directions(fixed_distance):
    rows = {r["driver"].split(" (")[0]: r for r in scenarios.tornado(hand_inputs())}
    # A wider price gap helps; dearer ships, fuel and money hurt.
    assert rows["Price spread"]["high_margin"] > rows["Price spread"]["low_margin"]
    assert rows["Vessel hire rate"]["high_margin"] < rows["Vessel hire rate"]["low_margin"]
    assert rows["Bunker price"]["high_margin"] < rows["Bunker price"]["low_margin"]
    assert rows["Interest rate"]["high_margin"] < rows["Interest rate"]["low_margin"]
    assert rows["Delay at port"]["high_margin"] < rows["Delay at port"]["base"]


def test_tornado_hire_swing_by_hand(fixed_distance):
    rows = {r["driver"].split(" (")[0]: r for r in scenarios.tornado(hand_inputs())}
    # Hire is $3,260,000 = $3.26 a barrel. Flexing it 25% each way moves freight by
    # $0.815 each way, and insurance on that freight by a hair (x 110% x 0.05%).
    expected_swing = 2 * 0.815 * (1 + 1.10 * 0.0005)
    assert rows["Vessel hire rate"]["swing"] == pytest.approx(expected_swing)


def test_tornado_is_sorted_biggest_first(fixed_distance):
    swings = [r["swing"] for r in scenarios.tornado(hand_inputs())]
    assert swings == sorted(swings, reverse=True)


def test_historical_run_matches_single_runs(fixed_distance):
    prices = pd.DataFrame(
        {"wti": [70.0, 80.0, None], "brent": [75.0, 90.0, 95.0]},
        index=pd.to_datetime(["2025-01-01", "2025-01-02", "2025-01-03"]),
    )
    history = scenarios.historical_run(prices, hand_inputs(), "wti", "brent")
    # The day with a missing price is dropped.
    assert len(history) == 2
    # The second day is exactly the hand-worked trade.
    assert history["margin"].iloc[1] == pytest.approx(3.92758086)
    assert history["spread"].iloc[0] == pytest.approx(5.0)


def test_historical_run_can_move_bunkers_with_brent(fixed_distance):
    prices = pd.DataFrame({"wti": [80.0], "brent": [90.0]}, index=pd.to_datetime(["2025-01-02"]))
    # Ratio 6.6667 makes bunkers 90 x 6.6667 = $600, the hand-worked value.
    history = scenarios.historical_run(prices, hand_inputs(bunker_usd_per_tonne=999), "wti",
                                       "brent", bunker_ratio=600 / 90)
    assert history["margin"].iloc[0] == pytest.approx(3.92758086)
