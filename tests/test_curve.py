"""The futures curve: what contango or backwardation does to a hedged cargo."""

import pandas as pd
import pytest

from engine import arbitrage, costs
from engine import prices
from tests.test_arbitrage import hand_inputs


def test_roll_value_by_hand():
    # A $0.60 a month contango over 36 days: 0.60 x 36 / 30 = +$0.72 a barrel.
    assert costs.curve_roll_value(0.60, 36) == pytest.approx(0.72)
    # Backwardation of $0.45 a month over 20 days: -0.45 x 20 / 30 = -$0.30.
    assert costs.curve_roll_value(-0.45, 20) == pytest.approx(-0.30)


def test_flat_curve_changes_nothing(fixed_distance):
    r = arbitrage.run(hand_inputs())
    assert r.curve_value == 0
    assert r.margin_per_bbl == pytest.approx(3.92758086)


def test_contango_adds_to_the_hand_worked_trade(fixed_distance):
    # The hand-worked trade is financed for 34 days: 0.60 x 34 / 30 = +$0.68 a barrel.
    r = arbitrage.run(hand_inputs(curve_m2_minus_m1=0.60))
    assert r.curve_value == pytest.approx(0.68)
    # Transit loss is on the oil, not on the hedge, so the margin rises by exactly $0.68.
    assert r.margin_per_bbl == pytest.approx(3.92758086 + 0.68)
    assert r.sale_value == pytest.approx(90.65 + 0.68)


def test_delay_lengthens_the_curve_effect(fixed_distance):
    # 3 days of delay: financed 37 days, so 0.60 x 37 / 30 = $0.74.
    r = arbitrage.run(hand_inputs(curve_m2_minus_m1=0.60, delay_days=3))
    assert r.curve_value == pytest.approx(0.74)


def test_curve_history_file_is_sensible():
    history = prices.curve_history()
    assert history.index.min() == pd.Timestamp("1985-01-01")
    assert history.index.max() == pd.Timestamp("2024-04-01")
    # April 2020, when US storage filled up, is the record contango in the series.
    assert history.idxmax() == pd.Timestamp("2020-04-01")
    assert -1.0 < history.median() < 1.0
