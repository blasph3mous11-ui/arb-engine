"""Voyage calculator, checked against a voyage worked out by hand."""

import dataclasses

import pytest

from engine import assumptions as A
from engine import voyage
from engine.voyage import Vessel, estimate_voyage, suez_toll_usd

# A test ship with round numbers (these match the Suezmax assumptions).
SHIP = Vessel(
    key="test", name="Test Suezmax", cargo_capacity_bbl=1_000_000,
    laden_speed_knots=13.0, ballast_speed_knots=12.5,
    laden_consumption_tpd=44, ballast_consumption_tpd=35,
    load_port_consumption_tpd=12, discharge_port_consumption_tpd=71, idle_consumption_tpd=7.5,
    suez_canal_net_tonnage=81_000, can_transit_suez_laden=True,
    port_cost_factor=1.0, hull_value_usd=80_000_000,
)
COMMON = dict(vessel=SHIP, distance_nm=9360, cargo_bbl=1_000_000, hire_usd_per_day=50_000,
              bunker_usd_per_tonne=600, load_port_cost_usd=78_000, discharge_port_cost_usd=150_000,
              load_days=2, discharge_days=2)


def test_cape_round_voyage_by_hand():
    v = estimate_voyage(via="cape", **COMMON)
    # Laden: 9,360 / (13 x 24) = 30.0 days. Ballast: 9,360 / (12.5 x 24) = 31.2 days.
    assert v.days["laden_sea"] == pytest.approx(30.0)
    assert v.days["ballast_sea"] == pytest.approx(31.2)
    # Total: 2 load + 30 + 2 discharge + 31.2 = 65.2 days.
    assert v.total_days == pytest.approx(65.2)
    # Fuel: 2x12 + 30x44 + 2x71 + 31.2x35 = 24 + 1,320 + 142 + 1,092 = 2,578 tonnes.
    assert v.total_fuel_tonnes == pytest.approx(2578)
    # Hire: 65.2 x $50,000 = $3,260,000. Fuel: 2,578 x $600 = $1,546,800. Ports: $228,000.
    assert v.costs["Vessel hire"] == pytest.approx(3_260_000)
    assert v.costs["Bunkers (fuel)"] == pytest.approx(1_546_800)
    assert v.costs["Port charges"] == pytest.approx(228_000)
    assert v.costs["Canal tolls"] == 0
    assert v.costs["War-risk premium"] == 0
    # Total $5,034,800 over 1,000,000 barrels = $5.0348 a barrel.
    assert v.total_cost == pytest.approx(5_034_800)
    assert v.cost_per_bbl == pytest.approx(5.0348)


def test_suez_round_voyage_by_hand():
    v = estimate_voyage(via="suez", canal_delay_days=1, canal_toll_laden_usd=500_000,
                        canal_toll_ballast_usd=400_000, war_risk_usd_per_transit=100_000, **COMMON)
    # One extra day in the canal each way: 65.2 + 2 = 67.2 days.
    assert v.total_days == pytest.approx(67.2)
    # Canal days burn idle fuel: 2,578 + 2 x 7.5 = 2,593 tonnes.
    assert v.total_fuel_tonnes == pytest.approx(2593)
    # Hire 67.2 x 50,000 = 3,360,000; fuel 2,593 x 600 = 1,555,800; ports 228,000;
    # tolls 500,000 + 400,000 = 900,000; war risk 2 transits x 100,000 = 200,000.
    assert v.total_cost == pytest.approx(3_360_000 + 1_555_800 + 228_000 + 900_000 + 200_000)


def test_one_way_voyage_drops_the_empty_leg():
    v = estimate_voyage(via="cape", charge_ballast_leg=False, **COMMON)
    # 2 + 30 + 2 = 34 days, no ballast leg.
    assert v.total_days == pytest.approx(34.0)
    assert v.laden_days == pytest.approx(34.0)


def test_port_cost_scales_with_ship_size():
    big = dataclasses.replace(SHIP, port_cost_factor=1.4)
    v = estimate_voyage(via="cape", **{**COMMON, "vessel": big})
    assert v.costs["Port charges"] == pytest.approx(228_000 * 1.4)


def test_laden_vlcc_cannot_use_suez():
    with pytest.raises(ValueError):
        estimate_voyage(via="suez", **{**COMMON, "vessel": voyage.get_vessel("vlcc")})


def test_cargo_larger_than_ship_is_rejected():
    with pytest.raises(ValueError):
        estimate_voyage(via="cape", **{**COMMON, "cargo_bbl": 1_500_000})


def _toll_factors(laden: bool) -> float:
    canal = A.load("ports")["suez_canal"]
    surcharge = A.val(canal["laden_surcharge_pct" if laden else "ballast_surcharge_pct"])
    return (1 + surcharge / 100) * A.val(canal["usd_per_sdr"])


def test_suez_toll_laden_suezmax_by_hand():
    # 81,000 SCNT, laden crude tanker, 2024 tariff (SDR per ton by band):
    #   5,000 x 11.04 = 55,200     5,000 x 7.82 = 39,100    10,000 x 5.91 = 59,100
    #  20,000 x 2.93 = 58,600     30,000 x 2.53 = 75,900    11,000 x 2.17 = 23,870
    #  total 311,770 SDR, then the surcharge and the SDR-to-dollar rate.
    assert suez_toll_usd(81_000, laden=True) == pytest.approx(311_770 * _toll_factors(True))
    # With the 37% surcharge and $1.36 per SDR that is about $581,000.
    assert 500_000 < suez_toll_usd(81_000, laden=True) < 650_000


def test_suez_toll_first_band_ballast():
    # 5,000 SCNT in ballast: 5,000 x 9.40 = 47,000 SDR.
    assert suez_toll_usd(5_000, laden=False) == pytest.approx(47_000 * _toll_factors(False))


def test_suez_toll_above_last_band():
    # 130,000 SCNT laden: the six bands (120,000 tons) come to
    # 55,200 + 39,100 + 59,100 + 58,600 + 75,900 + 50,000 x 2.17 (108,500) = 396,400 SDR,
    # plus "the rest": 10,000 x 2.13 = 21,300. Total 417,700 SDR.
    assert suez_toll_usd(130_000, laden=True) == pytest.approx(417_700 * _toll_factors(True))


# --- Checks on the routing library and the real assumptions ----------------

def test_route_distances_match_published_tables():
    ref = A.load("ports")["reference_distances"]
    suez, _ = voyage.sea_route("houston", "mumbai", "suez")
    cape, _ = voyage.sea_route("houston", "mumbai", "cape")
    assert suez == pytest.approx(A.val(ref["houston_mumbai_via_suez_nm"]), rel=0.06)
    assert cape == pytest.approx(A.val(ref["houston_mumbai_via_cape_nm"]), rel=0.06)
    assert cape > suez + 1500  # the Cape detour adds a couple of thousand miles


def test_calm_market_freight_is_a_few_dollars_a_barrel():
    hire = A.get("market", "freight_markets", "calm_2024", "hire_usd_per_day", "suezmax")
    for via in ("suez", "cape"):
        v = voyage.voyage_from_assumptions("corpus_christi", "sikka", "suezmax", via,
                                           hire_usd_per_day=hire, bunker_usd_per_tonne=600)
        assert 2.0 < v.cost_per_bbl < 8.0, f"{via}: ${v.cost_per_bbl:.2f}/bbl looks wrong"
