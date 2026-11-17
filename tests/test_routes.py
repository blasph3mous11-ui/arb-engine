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


def test_calm_market_freight_is_sensible_for_every_ship_and_route():
    # "A few dollars a barrel" holds for the big ships; small ships on long hauls cost more.
    upper = {"vlcc": 6.0, "suezmax": 9.0, "suezmax_eco": 9.0, "aframax": 11.0, "panamax": 12.0}
    calm = A.load("market")["freight_markets"]["calm_2024"]["hire_usd_per_day"]
    for origin in ("houston", "loop"):
        for destination in ("rotterdam", "sikka", "ningbo", "ulsan"):
            for ship in voyage.vessel_keys():
                for via in voyage.route_options(origin, destination, ship):
                    v = voyage.voyage_from_assumptions(origin, destination, ship, via,
                                                       hire_usd_per_day=A.val(calm[ship]),
                                                       bunker_usd_per_tonne=600)
                    assert 1.0 < v.cost_per_bbl < upper[ship], \
                        f"{origin}-{destination} {ship} {via}: ${v.cost_per_bbl:.2f}/bbl"


def test_every_route_ends_at_its_port():
    # Guards against the routing network stopping short of, or past, a port (Paradip was 85 nm out).
    for origin in voyage.port_keys("origin"):
        for destination in voyage.port_keys("destination"):
            for via in voyage.route_options(origin, destination, "suezmax"):
                _, points = voyage.sea_route(origin, destination, via)
                o, d = voyage.get_port(origin), voyage.get_port(destination)
                assert voyage.great_circle_nm(points[0], (o["longitude"], o["latitude"])) <= 25
                assert voyage.great_circle_nm(points[-1], (d["longitude"], d["latitude"])) <= 25


def test_great_circle_by_hand():
    # One degree of latitude along a meridian is 60 nautical miles (to within 0.1%).
    assert voyage.great_circle_nm((0, 0), (0, 1)) == pytest.approx(60.04, abs=0.05)


def test_draught_warning_only_where_the_channel_is_too_shallow():
    # LOOP is offshore deep water: no warning for any ship, including a VLCC.
    assert all(voyage.draught_warning("loop", ship) is None for ship in voyage.vessel_keys())
    # Corpus Christi (54 ft) takes a full Suezmax (50 ft) but not a full VLCC (70 ft).
    assert voyage.draught_warning("corpus_christi", "suezmax") is None
    assert "VLCC" in voyage.draught_warning("corpus_christi", "vlcc")
    # Beaumont (40 ft) is too shallow for a full Suezmax.
    assert "40 ft" in voyage.draught_warning("beaumont", "suezmax")


def test_every_ship_has_a_hire_rate_in_every_freight_market():
    for market in A.load("market")["freight_markets"].values():
        assert set(market["hire_usd_per_day"]) == set(voyage.vessel_keys())
