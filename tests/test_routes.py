"""Route choice: which routes exist for a voyage and ship, and what each one is charged."""

import dataclasses

import pytest

from engine import assumptions as A
from engine import voyage
from engine.voyage import estimate_voyage
from tests.test_voyage import COMMON, SHIP


# --- Which routes exist (the routing library is replaced, so the logic is checked by hand) ---

def test_voyage_through_suez_offers_suez_and_cape(monkeypatch):
    monkeypatch.setattr(voyage, "shortest_path_uses_suez", lambda origin, destination: True)
    assert voyage.route_options("corpus_christi", "sikka", "suezmax") == ["suez", "cape"]


def test_ship_too_deep_for_the_canal_only_gets_the_cape(monkeypatch):
    monkeypatch.setattr(voyage, "shortest_path_uses_suez", lambda origin, destination: True)
    # A fully laden VLCC cannot pass the Suez Canal, so Suez is not offered.
    assert voyage.route_options("corpus_christi", "sikka", "vlcc") == ["cape"]


def test_voyage_that_never_nears_suez_is_direct(monkeypatch):
    monkeypatch.setattr(voyage, "shortest_path_uses_suez", lambda origin, destination: False)
    # Across the Atlantic there is no canal and no choice, whatever the ship.
    assert voyage.route_options("houston", "rotterdam", "suezmax") == ["direct"]
    assert voyage.route_options("houston", "rotterdam", "vlcc") == ["direct"]


def test_route_that_does_not_exist_is_refused(monkeypatch):
    monkeypatch.setattr(voyage, "shortest_path_uses_suez", lambda origin, destination: False)
    monkeypatch.setattr(voyage, "sea_route", lambda origin, destination, via: (5000, ()))
    # Asking for Suez on an Atlantic crossing must fail, not quietly charge a toll.
    with pytest.raises(ValueError):
        voyage.voyage_from_assumptions("houston", "rotterdam", "suezmax", "suez",
                                       hire_usd_per_day=50_000, bunker_usd_per_tonne=600)


# --- What a direct route is charged, by hand ---------------------------------------------

def test_direct_voyage_by_hand():
    # 4,992 nm across the Atlantic: laden 4,992 / (13 x 24) = 16.0 days,
    # ballast 4,992 / (12.5 x 24) = 16.64 days, plus 2 days at each port = 36.64 days.
    v = estimate_voyage(via="direct", canal_delay_days=1, canal_toll_laden_usd=500_000,
                        canal_toll_ballast_usd=400_000, war_risk_usd_per_transit=100_000,
                        **{**COMMON, "distance_nm": 4992})
    assert v.days["laden_sea"] == pytest.approx(16.0)
    assert v.total_days == pytest.approx(36.64)
    # No canal: no canal days, no toll and no war-risk premium, even though they were supplied.
    assert v.days["laden_canal"] == 0 and v.days["ballast_canal"] == 0
    assert v.costs["Canal tolls"] == 0
    assert v.costs["War-risk premium"] == 0
    # Fuel: 2x12 + 16x44 + 2x71 + 16.64x35 = 24 + 704 + 142 + 582.4 = 1,452.4 tonnes.
    assert v.total_fuel_tonnes == pytest.approx(1452.4)
    # Hire 36.64 x 50,000 = 1,832,000; fuel 1,452.4 x 600 = 871,440; ports 228,000.
    assert v.total_cost == pytest.approx(1_832_000 + 871_440 + 228_000)


def test_smaller_ship_pays_smaller_port_bill_and_carries_less():
    panamax = voyage.get_vessel("panamax")
    assert panamax.cargo_capacity_bbl == 500_000
    small = dataclasses.replace(SHIP, port_cost_factor=0.65, cargo_capacity_bbl=500_000)
    v = estimate_voyage(via="cape", **{**COMMON, "vessel": small, "cargo_bbl": 500_000})
    # Ports: (78,000 + 150,000) x 0.65 = 148,200.
    assert v.costs["Port charges"] == pytest.approx(148_200)
    # Same ship days and fuel as the hand-worked Cape voyage, spread over half the barrels:
    # (3,260,000 + 1,546,800 + 148,200) / 500,000 = $9.91 a barrel.
    assert v.cost_per_bbl == pytest.approx(9.91)


# --- Checks on the real routing library and the real port list ---------------------------

def test_every_port_pair_has_a_sensible_route():
    for origin in voyage.port_keys("origin"):
        for destination in voyage.port_keys("destination"):
            options = voyage.route_options(origin, destination, "suezmax")
            region = voyage.get_port(destination)["region"]
            if region == "europe":
                assert options == ["direct"], f"{origin}-{destination}: {options}"
            else:
                assert options == ["suez", "cape"], f"{origin}-{destination}: {options}"
                suez, _ = voyage.sea_route(origin, destination, "suez")
                cape, _ = voyage.sea_route(origin, destination, "cape")
                assert cape > suez + 1000, f"{origin}-{destination}: Cape {cape:.0f} vs Suez {suez:.0f}"


def test_atlantic_crossing_matches_published_distance():
    ref = A.load("ports")["reference_distances"]["houston_rotterdam_nm"]
    distance, _ = voyage.sea_route("houston", "rotterdam", "direct")
    assert distance == pytest.approx(A.val(ref), rel=0.06)


def test_eco_ship_burns_less_than_the_older_design():
    old = voyage.voyage_from_assumptions("corpus_christi", "sikka", "suezmax", "cape", 30_000, 600)
    eco = voyage.voyage_from_assumptions("corpus_christi", "sikka", "suezmax_eco", "cape", 30_000, 600)
    assert eco.total_days == pytest.approx(old.total_days)       # same speed, same route
    assert eco.total_fuel_tonnes < old.total_fuel_tonnes * 0.85  # at least 15% less fuel


def test_calm_market_freight_on_new_routes_is_a_few_dollars_a_barrel():
    calm = A.load("market")["freight_markets"]["calm_2024"]["hire_usd_per_day"]
    for origin, destination, ship in (("houston", "rotterdam", "aframax"), ("loop", "ningbo", "vlcc"),
                                      ("beaumont", "singapore", "suezmax"), ("houston", "rotterdam", "panamax")):
        via = voyage.route_options(origin, destination, ship)[-1]
        v = voyage.voyage_from_assumptions(origin, destination, ship, via,
                                           hire_usd_per_day=A.val(calm[ship]), bunker_usd_per_tonne=600)
        assert 1.5 < v.cost_per_bbl < 9.0, f"{origin}-{destination} {ship}: ${v.cost_per_bbl:.2f}/bbl"


def test_every_ship_has_a_hire_rate_in_every_freight_market():
    for market in A.load("market")["freight_markets"].values():
        assert set(market["hire_usd_per_day"]) == set(voyage.vessel_keys())
