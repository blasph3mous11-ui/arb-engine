"""Scenario tools: break-even, tornado and the historical re-run."""

import pandas as pd
import pytest

from engine import arbitrage, prices, scenarios
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


def test_tornado_interest_label_matches_the_cut_actually_made(fixed_distance):
    def interest_row(rate_pct):
        rows = scenarios.tornado(hand_inputs(interest_rate_pct=rate_pct))
        return next(r for r in rows if r["driver"].startswith("Interest rate"))

    # The tornado flexes interest by 2 points. From 6% that is a full cut to 4%.
    assert interest_row(6.0)["low_label"] == "-2 pts"
    # From 1% the rate can only fall 1 point, to zero, and the label must say so.
    row = interest_row(1.0)
    assert row["low_label"] == "-1.00 pts (cannot go below 0%)"
    # Financing is in proportion to the rate, so cutting 1% to 0% gains exactly
    # half of what raising 1% to 3% loses.
    gain, loss = row["low_margin"] - row["base"], row["base"] - row["high_margin"]
    assert gain == pytest.approx(loss / 2)
    # From 0% nothing can be cut at all.
    row = interest_row(0.0)
    assert row["low_label"] == "no change (already 0%)"
    assert row["low_margin"] == pytest.approx(row["base"])


def test_tornado_has_no_use_suez_row_when_the_canal_is_closed(fixed_distance):
    # The hand-worked trade goes via the Cape on a Suezmax, which could use the canal.
    drivers = [r["driver"] for r in scenarios.tornado(hand_inputs())]
    assert "Use Suez instead of Cape" in drivers
    drivers = [r["driver"] for r in scenarios.tornado(hand_inputs(), suez_open=False)]
    assert "Use Suez instead of Cape" not in drivers


def test_historical_run_on_monthly_averages_for_dubai(fixed_distance):
    # Dubai is published as one average per month. Here it is $90.00 all month
    # while daily WTI is 70, 80 and 90: an average of $80.00.
    daily = pd.DataFrame(
        {"wti": [70.0, 80.0, 90.0], "brent": [85.0, 90.0, 95.0], "dubai": [90.0, 90.0, 90.0]},
        index=pd.to_datetime(["2025-01-02", "2025-01-03", "2025-01-06"]),
    )
    monthly = prices.monthly_averages(daily)
    inputs = hand_inputs(destination_benchmark="dubai")
    history = scenarios.historical_run(monthly, inputs, "wti", "dubai")
    # One row for the month, not three daily rows with gaps of 20, 10 and 0.
    assert len(history) == 1
    assert history.index[0] == pd.Timestamp("2025-01-01")
    # Spread = month-average Dubai 90 minus month-average WTI 80 = $10.00.
    assert history["spread"].iloc[0] == pytest.approx(10.0)
    # And it is the same answer as a single run at those two averages.
    single = arbitrage.run(inputs.with_changes(origin_benchmark_price=80.0,
                                               destination_benchmark_price=90.0))
    assert history["margin"].iloc[0] == pytest.approx(single.margin_per_bbl)
    # With fuel following Brent, the month-average Brent (90) is used:
    # 90 x 6.6667 = $600 a tonne, the hand-worked fuel price, so the margin is unchanged.
    moving = scenarios.historical_run(monthly, inputs.with_changes(bunker_usd_per_tonne=999),
                                      "wti", "dubai", bunker_ratio=600 / 90)
    assert moving["margin"].iloc[0] == pytest.approx(single.margin_per_bbl)


def test_margin_grid_cell_is_the_hand_worked_trade(fixed_distance):
    # Hire $50,000 a day and a $10 spread is exactly the hand-worked trade: $3.9276 a barrel.
    grid = scenarios.margin_grid(hand_inputs(), [25_000, 50_000], [5.0, 10.0])
    assert grid.loc[10.0, 50_000] == pytest.approx(3.92758086)
    # A $5 narrower gap costs $5 less the 0.2% transit loss on it: 5 x 0.998 = $4.99.
    assert grid.loc[5.0, 50_000] == pytest.approx(3.92758086 - 4.99)
    # Halving hire saves 65.2 days x $25,000 = $1.63 a barrel, plus the insurance on it
    # (x 110% x 0.05%).
    assert grid.loc[10.0, 25_000] == pytest.approx(3.92758086 + 1.63 * (1 + 1.10 * 0.0005))


def test_margin_grid_agrees_with_breakeven(fixed_distance):
    inputs = hand_inputs()
    breakeven = scenarios.breakeven_spread(inputs)
    grid = scenarios.margin_grid(inputs, [inputs.hire_usd_per_day], [breakeven])
    assert grid.iloc[0, 0] == pytest.approx(0, abs=1e-6)


def test_grid_axes_come_from_the_yaml_settings():
    hires, spreads = scenarios.grid_axes()
    assert len(hires) == len(spreads) == 16
    assert hires[0] == 10_000 and hires[-1] == 500_000
    assert spreads[0] == -5 and spreads[-1] == 40
