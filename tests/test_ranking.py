"""Destination ranking: the same trade costed to every discharge port, best first."""

import pytest

from engine import arbitrage, ranking, voyage
from tests.conftest import HAND_DISTANCE_NM
from tests.test_arbitrage import hand_inputs


def test_cheapest_route_is_chosen_by_hand(fixed_distance):
    # With the sea distance fixed at 9,360 nm for both routes, Suez and the Cape take
    # the same sailing time, so Suez is simply the Cape voyage plus the canal costs
    # (two canal days, tolls, war-risk cover). The Cape must therefore be the cheaper route,
    # and the result must be the hand-worked Cape trade: margin $3.9276 a barrel.
    best = ranking.best_route_result(hand_inputs(via="suez"), "sikka")
    assert best.voyage.via == "cape"
    assert best.margin_per_bbl == pytest.approx(3.92758086)


def test_ranking_orders_ports_by_margin(monkeypatch):
    # Two ports only, at hand-picked distances: the nearer one costs less to reach
    # and both sell at the same price, so the nearer port must rank first.
    distances = {"rotterdam": 4992, "sikka": HAND_DISTANCE_NM}
    monkeypatch.setattr(voyage, "port_keys", lambda role: list(distances))
    monkeypatch.setattr(voyage, "shortest_path_uses_suez", lambda origin, destination: False)
    monkeypatch.setattr(voyage, "sea_route", lambda origin, destination, via: (distances[destination], ()))

    rows = ranking.rank_destinations(hand_inputs(via="direct"))
    assert [row["key"] for row in rows] == ["rotterdam", "sikka"]

    # Sikka at 9,360 nm with no canal is the hand-worked voyage: freight $5.0348 a barrel.
    sikka = rows[1]
    assert sikka["freight"] == pytest.approx(5.0348)
    assert sikka["margin"] == pytest.approx(3.92758086)

    # Rotterdam at 4,992 nm: 36.64 ship days and 1,452.4 t of fuel (see test_routes.py).
    # Hire 36.64 x 50,000 = 1,832,000; fuel 1,452.4 x 600 = 871,440;
    # ports (78,000 + 130,000) = 208,000. Total $2,911,440 = $2.91144 a barrel.
    rotterdam = rows[0]
    assert rotterdam["freight"] == pytest.approx(2.91144)
    assert rotterdam["days_loaded"] == pytest.approx(20.0)   # 2 + 16 + 2
    assert rotterdam["margin"] > sikka["margin"]
    # Each row adds up: sale value minus landed cost is the margin.
    for row in rows:
        assert row["sale_value"] - row["landed_cost"] == pytest.approx(row["margin"])
        assert row["landed_cost"] == pytest.approx(81.0 + row["freight"] + row["other_costs"])


def test_every_destination_is_ranked_once_with_a_real_route():
    inputs = arbitrage.default_inputs(80.0, 90.0, 600.0)
    rows = ranking.rank_destinations(inputs)
    assert sorted(row["key"] for row in rows) == sorted(voyage.port_keys("destination"))
    assert [row["margin"] for row in rows] == sorted((row["margin"] for row in rows), reverse=True)
    for row in rows:
        assert row["via"] in voyage.route_options(inputs.origin_key, row["key"], inputs.vessel_key)


def test_a_ship_too_deep_for_suez_is_ranked_via_the_cape():
    inputs = arbitrage.default_inputs(80.0, 90.0, 600.0, vessel_key="vlcc", origin_key="loop", via="cape")
    for row in ranking.rank_destinations(inputs):
        assert row["via"] in ("cape", "direct")
