"""Ship speed: fuel at other speeds, the cheapest speed, and how it changes the trade."""

import pytest

from engine import arbitrage, voyage
from tests.test_arbitrage import hand_inputs


def test_fuel_at_another_speed_by_hand():
    # Aframax: 43 t/day at its usual 13 knots, of which 5 t/day (its idle figure) is burned
    # whatever the speed. 10% slower: 5 + 38 x 0.9^3 = 5 + 38 x 0.729 = 32.702 t/day.
    assert voyage.sea_consumption_tpd(43, 13, 11.7, 5) == pytest.approx(32.702)
    # At the usual speed it is the published figure.
    assert voyage.sea_consumption_tpd(43, 13, 13, 5) == pytest.approx(43)


def test_cheapest_speed_by_hand():
    # Suezmax loaded: 44 t/day at 13 knots, 7.5 t/day fixed, so 36.5 t/day from the engine.
    # Fuel $700/t, time $30,000/day.
    #   (30,000 + 700 x 7.5) / (2 x 700 x 36.5) = 35,250 / 51,100 = 0.68982
    #   13 x 0.68982^(1/3) = 13 x 0.88358 = 11.487 knots.
    assert voyage.cheapest_speed(30_000, 700, 44, 13, 7.5, 10, 15) == pytest.approx(11.4865, abs=1e-4)
    # At $151,000 a day the formula says 18.9 knots, beyond the ship: it goes flat out.
    assert voyage.cheapest_speed(151_000, 700, 44, 13, 7.5, 10, 15) == 15
    # When time costs nothing (or less), it sails as slowly as allowed.
    assert voyage.cheapest_speed(-100_000, 700, 44, 13, 7.5, 10, 15) == 10


def test_voyage_at_a_set_speed_by_hand(fixed_distance):
    # 9,360 nm at 12 knots = 9,360 / (24 x 12) = 32.5 days loaded (30.0 at the usual 13 knots).
    # Fuel per day: 7.5 + 36.5 x (12/13)^3 = 36.208 t; x 32.5 days = 1,176.77 t.
    r = arbitrage.run(hand_inputs(speed_mode="custom", laden_speed_knots=12, ballast_speed_knots=12.5))
    assert r.voyage.days["laden_sea"] == pytest.approx(32.5)
    assert r.voyage.fuel_tonnes["laden_sea"] == pytest.approx(1176.7678, abs=1e-3)
    # The empty leg is left at its usual 12.5 knots and published 35 t/day: 31.2 days, 1,092 t.
    assert r.voyage.days["ballast_sea"] == pytest.approx(31.2)
    assert r.voyage.fuel_tonnes["ballast_sea"] == pytest.approx(1092)
    assert r.voyage.speeds == {"laden": 12, "ballast": 12.5}


def test_usual_speed_changes_nothing(fixed_distance):
    usual = arbitrage.run(hand_inputs())
    assert usual.margin_per_bbl == pytest.approx(3.92758086)
    same = arbitrage.run(hand_inputs(speed_mode="custom", laden_speed_knots=13, ballast_speed_knots=12.5))
    assert same.margin_per_bbl == pytest.approx(usual.margin_per_bbl)


def test_cheapest_speed_by_hand_on_the_trade(fixed_distance):
    # At $30,000 a day, insurance adds 110% x 0.05% = 0.055% to hire and fuel (freight is insured),
    # and the cargo costs $81m x 6% / 360 = $13,500 a day in interest while loaded:
    #   loaded: time 1.00055 x 30,000 + 13,500 = $43,516.50; fuel 1.00055 x 600 = $600.33
    #           13 x [(43,516.50 + 600.33 x 7.5) / (2 x 600.33 x 36.5)]^(1/3) = 13.402 knots
    #   empty:  12.5 x [(30,016.50 + 600.33 x 7.5) / (2 x 600.33 x 27.5)]^(1/3) = 12.687 knots
    laden, ballast = arbitrage.ship_speeds(hand_inputs(hire_usd_per_day=30_000, speed_mode="cheapest"))
    assert laden == pytest.approx(13.4022, abs=1e-4)
    assert ballast == pytest.approx(12.6866, abs=1e-4)


def test_cheapest_speed_really_is_the_best_margin(fixed_distance):
    """Check the formula against the whole model: no other speed in the range does better."""
    cheapest = hand_inputs(hire_usd_per_day=30_000, speed_mode="cheapest")
    laden, ballast = arbitrage.ship_speeds(cheapest)
    best = arbitrage.run(cheapest).margin_per_bbl
    for tenths in range(100, 151):
        knots = tenths / 10
        for speeds in ((knots, ballast), (laden, knots)):
            other = hand_inputs(hire_usd_per_day=30_000, speed_mode="custom",
                                laden_speed_knots=speeds[0], ballast_speed_knots=speeds[1])
            assert arbitrage.run(other).margin_per_bbl <= best + 1e-9
    # And it beats the usual speed.
    assert best > arbitrage.run(hand_inputs(hire_usd_per_day=30_000)).margin_per_bbl


def test_the_cost_curve_bottoms_out_at_the_cheapest_speed(fixed_distance):
    inputs = hand_inputs(hire_usd_per_day=30_000, speed_mode="cheapest")
    laden, _ = arbitrage.ship_speeds(inputs)
    rows = arbitrage.speed_cost_curve(inputs, fixed_distance, [k / 100 for k in range(1000, 1501)])
    lowest = min(rows, key=lambda row: row["total"])
    assert lowest["knots"] == pytest.approx(laden, abs=0.01)
    # Faster always means less time and more fuel.
    assert rows[0]["time"] > rows[-1]["time"] and rows[0]["fuel"] < rows[-1]["fuel"]


def test_dearer_ships_sail_faster(fixed_distance):
    calm = arbitrage.ship_speeds(hand_inputs(hire_usd_per_day=30_000, speed_mode="cheapest"))
    dear = arbitrage.ship_speeds(hand_inputs(hire_usd_per_day=151_000, speed_mode="cheapest"))
    assert dear[0] > calm[0] and dear[1] > calm[1]
    assert dear == (15, 15)  # at that rate both legs go as fast as allowed


def test_contango_slows_the_loaded_leg(fixed_distance):
    flat = arbitrage.ship_speeds(hand_inputs(hire_usd_per_day=30_000, speed_mode="cheapest"))
    # $0.60 a month on a million barrels = $20,000 a day earned by being at sea: slower pays.
    mild = arbitrage.ship_speeds(hand_inputs(hire_usd_per_day=30_000, speed_mode="cheapest",
                                             curve_m2_minus_m1=0.60))
    assert mild[0] < flat[0] and mild[1] == flat[1]
    # $5 a month ($166,667 a day) is worth more than the ship and the interest: as slow as allowed.
    steep = arbitrage.ship_speeds(hand_inputs(hire_usd_per_day=30_000, speed_mode="cheapest",
                                              curve_m2_minus_m1=5.0))
    assert steep[0] == 10


def test_eu_carbon_slows_the_ship(fixed_distance, monkeypatch):
    monkeypatch.setattr(voyage, "shortest_path_uses_suez", lambda origin, destination: False)
    rotterdam = arbitrage.ship_speeds(hand_inputs(hire_usd_per_day=30_000, speed_mode="cheapest",
                                                  destination_key="rotterdam", via="direct"))
    sikka = arbitrage.ship_speeds(hand_inputs(hire_usd_per_day=30_000, speed_mode="cheapest",
                                              destination_key="sikka", via="direct"))
    assert rotterdam[0] < sikka[0] and rotterdam[1] < sikka[1]


def test_a_broker_quote_keeps_the_usual_speed(fixed_distance):
    # On a quote the shipowner pays the fuel and sets the speed.
    speeds = arbitrage.ship_speeds(hand_inputs(speed_mode="cheapest", freight_override_usd=5_000_000))
    assert speeds == (13, 12.5)


def test_speeds_outside_the_range_are_refused(fixed_distance):
    with pytest.raises(ValueError):
        arbitrage.run(hand_inputs(speed_mode="custom", laden_speed_knots=20))
    with pytest.raises(ValueError):
        arbitrage.run(hand_inputs(speed_mode="flat out"))
