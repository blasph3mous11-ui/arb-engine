"""Charges the cargo pays on top of freight: offshore top-up (reverse lightering) and EU carbon."""

import pytest

from engine import arbitrage, costs, voyage
from tests.test_arbitrage import hand_inputs


def test_lightering_cost_by_hand():
    # 2,000,000 barrels topped up at $0.60 a barrel = $1,200,000.
    assert costs.lightering_cost(2_000_000, 0.60) == pytest.approx(1_200_000)


def test_eu_ets_covered_fuel_by_hand():
    # The hand-worked Cape voyage: load 24 t, laden sea 1,320 t, discharge 142 t, ballast sea 1,092 t.
    fuel = {"load_port": 24, "laden_sea": 1320, "laden_canal": 0,
            "discharge_port": 142, "ballast_sea": 1092, "ballast_canal": 0}
    # Half of the sea fuel (1,320 + 1,092 = 2,412 -> 1,206) plus all of the berth fuel (142) = 1,348 t.
    # The load port is outside the EU, so its 24 t do not count.
    assert costs.eu_ets_covered_fuel(fuel, 50) == pytest.approx(1348)


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


def test_shallow_load_port_adds_lightering(fixed_distance):
    # Beaumont (40 ft) is too shallow for a full Suezmax: $0.60 a barrel on the whole cargo.
    r = arbitrage.run(hand_inputs(origin_key="beaumont"))
    assert r.cost_stack["Reverse lightering"] == pytest.approx(0.60)


def test_eu_port_adds_carbon_and_others_do_not(fixed_distance, monkeypatch):
    monkeypatch.setattr(voyage, "shortest_path_uses_suez", lambda origin, destination: False)
    rotterdam = arbitrage.run(hand_inputs(destination_key="rotterdam", via="direct"))
    sikka = arbitrage.run(hand_inputs(destination_key="sikka", via="direct"))
    assert sikka.cost_stack["EU carbon (ETS)"] == 0
    # The hand-worked voyage's fuel (see test above): 1,348 t covered -> $346,307.94 on a million barrels.
    assert rotterdam.cost_stack["EU carbon (ETS)"] == pytest.approx(0.34630794)


def test_draught_warning_and_lightering_agree():
    for origin in voyage.port_keys("origin"):
        for ship in voyage.vessel_keys():
            assert (voyage.draught_warning(origin, ship) is not None) == voyage.needs_lightering(origin, ship)
