"""Charges the cargo pays on top of freight: offshore top-up (reverse lightering) and EU carbon."""

import pytest

from engine import arbitrage, costs, voyage
from engine import assumptions as A
from tests.test_arbitrage import hand_inputs


def test_lightering_cost_by_hand():
    # 1,190,476 barrels loaded offshore at $1.00 a barrel = $1,190,476.
    assert costs.lightering_cost(1_190_476, 1.00) == pytest.approx(1_190_476)


def test_eu_ets_covered_fuel_by_hand():
    # The hand-worked Cape voyage: load 24 t, laden sea 1,320 t, discharge 142 t, ballast sea 1,092 t.
    fuel = {"load_port": 24, "laden_sea": 1320, "laden_canal": 0,
            "discharge_port": 142, "ballast_sea": 1092, "ballast_canal": 0}
    # Half of the sea fuel (1,320 + 1,092 = 2,412 -> 1,206) plus all of the berth fuel (142) = 1,348 t.
    # The load port is outside the EU, so its 24 t do not count.
    assert costs.eu_ets_covered_fuel(fuel, False, True, 50) == pytest.approx(1348)


def test_eu_ets_inside_the_scheme_and_outside_it():
    fuel = {"load_port": 24, "laden_sea": 1320, "laden_canal": 0,
            "discharge_port": 142, "ballast_sea": 1092, "ballast_canal": 0}
    # Norway to Rotterdam, both inside: all sea fuel (2,412) + both ports (24 + 142) = 2,578 t.
    assert costs.eu_ets_covered_fuel(fuel, True, True, 50) == pytest.approx(2578)
    # Norway to India: half the sea fuel (1,206) + the Norwegian load port (24) = 1,230 t.
    assert costs.eu_ets_covered_fuel(fuel, True, False, 50) == pytest.approx(1230)
    # US to India: nothing.
    assert costs.eu_ets_covered_fuel(fuel, False, False, 50) == 0


def test_eu_ets_cost_by_hand():
    # 1,348 t of fuel x 3.114 = 4,197.672 t of CO2, all covered in 2026,
    # x EUR 75 = EUR 314,825.40, x 1.10 = $346,307.94.
    assert costs.eu_ets_cost(1348, 3.114, 100, 75, 1.10) == pytest.approx(346_307.94)


def test_no_charges_on_the_hand_worked_trade(fixed_distance):
    # Corpus Christi (54 ft) takes a full Suezmax (50 ft) and Sikka is not in the EU.
    r = arbitrage.run(hand_inputs())
    assert r.cost_stack["Reverse lightering"] == 0
    assert r.cost_stack["EU carbon (ETS)"] == 0
    assert r.margin_per_bbl == pytest.approx(3.92758086)




def test_eu_port_adds_carbon_and_others_do_not(fixed_distance, monkeypatch):
    monkeypatch.setattr(voyage, "shortest_path_uses_suez", lambda origin, destination: False)
    rotterdam = arbitrage.run(hand_inputs(destination_key="rotterdam", via="direct"))
    sikka = arbitrage.run(hand_inputs(destination_key="sikka", via="direct"))
    assert sikka.cost_stack["EU carbon (ETS)"] == 0
    # The hand-worked voyage's fuel (see test above): 1,348 t covered x 3.114 t CO2 = 4,197.672 t of
    # CO2, all covered in 2026, at the allowance price and exchange rate in costs.yaml (read here so
    # that refreshing the dated price does not break the test). At EUR 75 and $1.10 this was
    # $346,307.94; at EUR 90 it is $415,569.53, on a million barrels.
    ets = A.load("costs")["eu_ets"]
    expected = 1348 * 3.114 * A.val(ets["eua_price_eur_per_tonne"]) * A.val(ets["usd_per_eur"]) / 1_000_000
    assert rotterdam.cost_stack["EU carbon (ETS)"] == pytest.approx(expected)


def test_draught_warning_and_lightering_agree():
    for origin in voyage.port_keys("origin"):
        for ship in voyage.vessel_keys():
            assert (voyage.draught_warning(origin, ship) is not None) == voyage.needs_lightering(origin, ship)


def test_lightered_share_by_hand():
    # VLCC (70 ft full, empty at 0.4 x 70 = 28 ft) at Houston (45 ft):
    # (70 - 45) / (70 - 28) = 25 / 42 = 0.5952 of the cargo is loaded offshore.
    assert voyage.lightered_share("houston", "vlcc") == pytest.approx(25 / 42)
    # Suezmax (50 ft, empty 20 ft) at Beaumont (40 ft): (50 - 40) / 30 = 1/3.
    assert voyage.lightered_share("beaumont", "suezmax") == pytest.approx(1 / 3)
    # No top-up where the ship fits.
    assert voyage.lightered_share("loop", "vlcc") == 0
    assert voyage.lightered_share("corpus_christi", "suezmax") == 0


def test_lightering_only_on_the_topped_up_barrels(fixed_distance):
    # Suezmax at Beaumont: a third of the cargo at $1.00 a barrel = $0.3333 per barrel of cargo.
    r = arbitrage.run(hand_inputs(origin_key="beaumont"))
    assert r.cost_stack["Reverse lightering"] == pytest.approx(1 / 3)
