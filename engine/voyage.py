"""Voyage calculator: turns a route and a ship into days and dollars.

The trading logic in one paragraph: a trader who ships a cargo pays for the
whole ship for the whole trip. That means the daily hire of the vessel for
every day it is tied up (including the empty trip back), all the fuel it
burns, port charges at both ends, and canal tolls if it takes the canal.
Divide that by the barrels on board and you have freight per barrel.
"""

import math
from dataclasses import dataclass, field
from functools import lru_cache

from engine import assumptions as A
from engine.units import sailing_days

ROUTES = {"suez": "Via Suez Canal", "cape": "Via Cape of Good Hope", "direct": "Direct (no canal)"}
# Sea lanes the model never uses. "northwest" is the Arctic Northwest Passage.
# The Panama Canal is left out on purpose: see data/assumptions/ports.yaml (routing).
ALWAYS_FORBIDDEN = ["northwest", "panama"]


def check_route(via: str) -> None:
    """Stop on a mistyped route. Without this, "Cape" would quietly be costed
    as the short Suez distance with no canal tolls: cheaper than either real route."""
    if via not in ROUTES:
        raise ValueError(f"Unknown route '{via}'; use 'suez', 'cape' or 'direct'.")


@dataclass(frozen=True)
class Vessel:
    key: str
    name: str
    cargo_capacity_bbl: float
    laden_speed_knots: float
    ballast_speed_knots: float
    laden_consumption_tpd: float
    ballast_consumption_tpd: float
    load_port_consumption_tpd: float
    discharge_port_consumption_tpd: float
    idle_consumption_tpd: float
    suez_canal_net_tonnage: float
    can_transit_suez_laden: bool
    port_cost_factor: float
    hull_value_usd: float
    laden_draught_ft: float


def vessel_keys() -> list[str]:
    return list(A.load("vessels").keys())


def get_vessel(key: str) -> Vessel:
    raw = A.load("vessels")[key]
    fields = {name: A.val(raw[name]) for name in Vessel.__dataclass_fields__ if name != "key"}
    return Vessel(key=key, **fields)


def port_keys(role: str) -> list[str]:
    ports = A.load("ports")["ports"]
    return [k for k, p in ports.items() if A.val(p["role"]) == role]


def get_port(key: str) -> dict:
    raw = A.load("ports")["ports"][key]
    return {
        "key": key,
        "name": A.val(raw["name"]),
        "latitude": A.val(raw["latitude"]),
        "longitude": A.val(raw["longitude"]),
        "port_cost_usd": A.val(raw["port_cost_usd"]),
        "port_cost_is_estimate": A.is_estimate(raw["port_cost_usd"]),
        "region": A.val(raw["region"]),
        # Only load ports carry a channel depth; it decides whether a full ship can leave.
        "channel_depth_ft": A.val(raw["channel_depth_ft"]) if "channel_depth_ft" in raw else None,
        "eu_ets": bool(A.val(raw["eu_ets"])) if "eu_ets" in raw else False,
        # Which free price series a cargo bought here is priced against (load ports only).
        "price_benchmark": A.val(raw["price_benchmark"]) if "price_benchmark" in raw else None,
    }


def needs_lightering(origin_key: str, vessel_key: str) -> bool:
    """True when a fully loaded ship is too deep to leave the load port's channel."""
    depth = get_port(origin_key)["channel_depth_ft"]
    return depth is not None and get_vessel(vessel_key).laden_draught_ft > depth


def lightered_share(origin_key: str, vessel_key: str) -> float:
    """Share of a full cargo that must be topped up offshore, 0 to 1.

    A ship's draught rises roughly in line with the cargo on board, from its
    empty (ballast) draught to its full draught. If the channel allows only part
    of that rise, the rest of the cargo has to be loaded offshore from smaller ships.
    """
    depth = get_port(origin_key)["channel_depth_ft"]
    vessel = get_vessel(vessel_key)
    if depth is None or vessel.laden_draught_ft <= depth:
        return 0.0
    empty = vessel.laden_draught_ft * A.get("costs", "lightering", "ballast_draught_share")
    return min(1.0, (vessel.laden_draught_ft - depth) / (vessel.laden_draught_ft - empty))


def draught_warning(origin_key: str, vessel_key: str) -> str | None:
    """Plain-language warning when a fully loaded ship is too deep for the load port's channel.

    The tool still costs a full cargo; in reality the ship would leave part-loaded
    and be topped up offshore (reverse lightering), which costs extra.
    """
    port, vessel = get_port(origin_key), get_vessel(vessel_key)
    depth = port["channel_depth_ft"]
    if depth is None or vessel.laden_draught_ft <= depth:
        return None
    return (f"A fully loaded {vessel.name} draws about {vessel.laden_draught_ft:.0f} ft of water, but "
            f"the channel at {port['name']} is about {depth:.0f} ft deep. In practice the ship would "
            "leave part-loaded and be topped up offshore by smaller ships (reverse lightering). The "
            "tool adds an estimated top-up cost per barrel to the trade (see the Arbitrage page).")


def _search(origin_key: str, destination_key: str, forbidden: list[str]) -> dict:
    """Shortest sea path between two ports, avoiding the named canals and straits."""
    import searoute  # imported here so the rest of the engine works without it

    origin, destination = get_port(origin_key), get_port(destination_key)
    return searoute.searoute(
        [origin["longitude"], origin["latitude"]],
        [destination["longitude"], destination["latitude"]],
        units="naut", restrictions=forbidden, return_passages=True,
    )


@lru_cache(maxsize=None)
def shortest_path_uses_suez(origin_key: str, destination_key: str) -> bool:
    """Does the shortest path between these ports go through the Suez Canal?

    US Gulf to India or Asia: yes. US Gulf to Europe: no, the ship just crosses
    the Atlantic, so there is no canal to pay for and no Suez-or-Cape choice.
    """
    passages = _search(origin_key, destination_key, ALWAYS_FORBIDDEN)["properties"]["traversed_passages"]
    return "suez" in passages


def route_options(origin_key: str, destination_key: str, vessel_key: str) -> list[str]:
    """The routes that really exist for this voyage and ship.

    "direct" when the shortest path does not touch Suez. Otherwise the choice is
    Suez or the Cape, except that a ship too deep to pass the canal fully laden
    (a VLCC) can only go round the Cape.
    """
    if not shortest_path_uses_suez(origin_key, destination_key):
        return ["direct"]
    return (["suez"] if get_vessel(vessel_key).can_transit_suez_laden else []) + ["cape"]


@lru_cache(maxsize=None)
def sea_route(origin_key: str, destination_key: str, via: str) -> tuple[float, tuple]:
    """Sea distance in nautical miles and the path as (longitude, latitude) points.

    Uses the open-source `searoute` library, which finds the shortest path over
    a network of shipping lanes. For the Cape route we forbid the Suez Canal,
    so the shortest remaining path goes round South Africa.
    """
    check_route(via)
    result = _search(origin_key, destination_key,
                     ALWAYS_FORBIDDEN + (["suez"] if via == "cape" else []))
    points = [tuple(p) for p in result["geometry"]["coordinates"]]
    length = float(result["properties"]["length"])
    # The routing network sometimes ends at a lane junction well past the port
    # (Paradip: 85 nm beyond it). Close the path at the nearest approach instead.
    origin, destination = get_port(origin_key), get_port(destination_key)
    points, length = _close_to_port(points, length, (destination["longitude"], destination["latitude"]))
    points.reverse()
    points, length = _close_to_port(points, length, (origin["longitude"], origin["latitude"]))
    points.reverse()
    return length, tuple(points)


EARTH_RADIUS_NM = 3440.065  # mean Earth radius in nautical miles
MAX_PORT_GAP_NM = 25        # a route ending further than this from the port is corrected


def great_circle_nm(a: tuple, b: tuple) -> float:
    """Shortest distance over the Earth between two (longitude, latitude) points, in nautical miles."""
    lon1, lat1, lon2, lat2 = map(math.radians, (*a, *b))
    cos_angle = (math.sin(lat1) * math.sin(lat2)
                 + math.cos(lat1) * math.cos(lat2) * math.cos(lon2 - lon1))
    return math.acos(max(-1.0, min(1.0, cos_angle))) * EARTH_RADIUS_NM


def _nearest_point_on_segment(start: tuple, end: tuple, port: tuple) -> tuple:
    """Point on a short straight segment closest to the port (flat-map approximation)."""
    scale = math.cos(math.radians(port[1]))  # a degree of longitude is shorter away from the equator
    dx, dy = (end[0] - start[0]) * scale, end[1] - start[1]
    px, py = (port[0] - start[0]) * scale, port[1] - start[1]
    t = max(0.0, min(1.0, (px * dx + py * dy) / (dx * dx + dy * dy))) if (dx or dy) else 0.0
    return (start[0] + t * (end[0] - start[0]), start[1] + t * (end[1] - start[1]))


def _close_to_port(points: list, length: float, port: tuple) -> tuple[list, float]:
    """If the path ends far from the port, cut it at its nearest approach and sail straight in.

    Only the last few legs are searched, and the distance is corrected by the
    miles removed and the short leg added. Ports already within 25 nm are left alone.
    """
    if great_circle_nm(points[-1], port) <= MAX_PORT_GAP_NM:
        return points, length
    best = None
    for i in range(max(0, len(points) - 6), len(points) - 1):
        candidate = _nearest_point_on_segment(points[i], points[i + 1], port)
        gap = great_circle_nm(candidate, port)
        if best is None or gap < best[0]:
            best = (gap, i, candidate)
    gap, i, cut = best
    removed = great_circle_nm(cut, points[i + 1]) + sum(
        great_circle_nm(points[j], points[j + 1]) for j in range(i + 1, len(points) - 1))
    return points[:i + 1] + [cut, port], length - removed + gap


def suez_toll_usd(net_tonnage: float, laden: bool) -> float:
    """Suez Canal toll for one crude-tanker transit, in US dollars.

    The canal charges per Suez Canal Net Ton on a sliding scale (the first
    5,000 tons are dearest, later bands cheaper), priced in SDR. On top of
    that sits a percentage surcharge. We convert to dollars at the end.
    """
    canal = A.load("ports")["suez_canal"]
    band_sizes = A.val(canal["band_sizes_scnt"])
    rates = A.val(canal["laden_rates_sdr_per_scnt" if laden else "ballast_rates_sdr_per_scnt"])
    surcharge_pct = A.val(canal["laden_surcharge_pct" if laden else "ballast_surcharge_pct"])

    remaining, dues_sdr = net_tonnage, 0.0
    for size, rate in zip(band_sizes, rates):
        tons_in_band = min(remaining, size)
        dues_sdr += tons_in_band * rate
        remaining -= tons_in_band
    dues_sdr += remaining * rates[-1]  # "the rest", above the last band

    return dues_sdr * (1 + surcharge_pct / 100) * A.val(canal["usd_per_sdr"])


@dataclass
class VoyageResult:
    via: str
    distance_nm: float
    cargo_bbl: float
    days: dict = field(default_factory=dict)         # days by activity
    fuel_tonnes: dict = field(default_factory=dict)  # fuel burned by activity
    costs: dict = field(default_factory=dict)        # dollars by component

    @property
    def total_days(self) -> float:
        return sum(self.days.values())

    @property
    def laden_days(self) -> float:
        """Days the cargo is on the water: loading to end of discharge."""
        d = self.days
        return d["load_port"] + d["laden_sea"] + d["laden_canal"] + d["discharge_port"]

    @property
    def total_fuel_tonnes(self) -> float:
        return sum(self.fuel_tonnes.values())

    @property
    def total_cost(self) -> float:
        return sum(self.costs.values())

    @property
    def cost_per_bbl(self) -> float:
        return self.total_cost / self.cargo_bbl

    def per_bbl(self) -> dict:
        return {name: cost / self.cargo_bbl for name, cost in self.costs.items()}


def estimate_voyage(
    vessel: Vessel,
    distance_nm: float,
    via: str,
    cargo_bbl: float,
    hire_usd_per_day: float,
    bunker_usd_per_tonne: float,
    load_port_cost_usd: float,
    discharge_port_cost_usd: float,
    load_days: float,
    discharge_days: float,
    charge_ballast_leg: bool = True,
    canal_delay_days: float = 0.0,
    canal_toll_laden_usd: float = 0.0,
    canal_toll_ballast_usd: float = 0.0,
    war_risk_usd_per_transit: float = 0.0,
) -> VoyageResult:
    """Work out days, fuel and cost for one voyage. Every input is explicit."""
    check_route(via)
    if via == "suez" and not vessel.can_transit_suez_laden:
        raise ValueError(f"A fully laden {vessel.name} is too deep for the Suez Canal.")
    if cargo_bbl > vessel.cargo_capacity_bbl:
        raise ValueError(f"A {vessel.name} cannot carry {cargo_bbl:,.0f} barrels.")

    # Only the Suez route passes the canal (and the Red Sea beyond it). "cape" and
    # "direct" pay no toll, lose no canal day and need no Red Sea war-risk cover.
    uses_canal = via == "suez"
    # The empty return leg: the ship sails home by the same route.
    ballast_factor = 1.0 if charge_ballast_leg else 0.0

    days = {
        "load_port": load_days,
        "laden_sea": sailing_days(distance_nm, vessel.laden_speed_knots),
        "laden_canal": canal_delay_days if uses_canal else 0.0,
        "discharge_port": discharge_days,
        "ballast_sea": sailing_days(distance_nm, vessel.ballast_speed_knots) * ballast_factor,
        "ballast_canal": (canal_delay_days if uses_canal else 0.0) * ballast_factor,
    }
    fuel = {
        "load_port": days["load_port"] * vessel.load_port_consumption_tpd,
        "laden_sea": days["laden_sea"] * vessel.laden_consumption_tpd,
        "laden_canal": days["laden_canal"] * vessel.idle_consumption_tpd,
        "discharge_port": days["discharge_port"] * vessel.discharge_port_consumption_tpd,
        "ballast_sea": days["ballast_sea"] * vessel.ballast_consumption_tpd,
        "ballast_canal": days["ballast_canal"] * vessel.idle_consumption_tpd,
    }
    canal_transits = (1 + ballast_factor) if uses_canal else 0
    costs = {
        "Vessel hire": sum(days.values()) * hire_usd_per_day,
        "Bunkers (fuel)": sum(fuel.values()) * bunker_usd_per_tonne,
        "Port charges": (load_port_cost_usd + discharge_port_cost_usd) * vessel.port_cost_factor,
        "Canal tolls": (canal_toll_laden_usd + canal_toll_ballast_usd * ballast_factor) if uses_canal else 0.0,
        "War-risk premium": war_risk_usd_per_transit * canal_transits,
    }
    return VoyageResult(via=via, distance_nm=distance_nm, cargo_bbl=cargo_bbl,
                        days=days, fuel_tonnes=fuel, costs=costs)


def voyage_from_assumptions(
    origin_key: str,
    destination_key: str,
    vessel_key: str,
    via: str,
    hire_usd_per_day: float,
    bunker_usd_per_tonne: float,
    cargo_bbl: float | None = None,
    charge_ballast_leg: bool | None = None,
    include_war_risk: bool = True,
) -> VoyageResult:
    """The same calculation, filling everything else in from the YAML files."""
    vessel = get_vessel(vessel_key)
    options = route_options(origin_key, destination_key, vessel_key)
    if via not in options:
        raise ValueError(f"Route '{via}' does not exist for this voyage and ship; choose from {options}.")
    distance_nm, _ = sea_route(origin_key, destination_key, via)
    ports = A.load("ports")
    if charge_ballast_leg is None:
        charge_ballast_leg = A.get("costs", "voyage_basis", "charge_ballast_leg")
    war_risk = 0.0
    if include_war_risk:
        war_risk = vessel.hull_value_usd * A.get("costs", "insurance", "red_sea_war_risk_pct_of_hull") / 100

    return estimate_voyage(
        vessel=vessel,
        distance_nm=distance_nm,
        via=via,
        cargo_bbl=cargo_bbl or vessel.cargo_capacity_bbl,
        hire_usd_per_day=hire_usd_per_day,
        bunker_usd_per_tonne=bunker_usd_per_tonne,
        load_port_cost_usd=get_port(origin_key)["port_cost_usd"],
        discharge_port_cost_usd=get_port(destination_key)["port_cost_usd"],
        load_days=A.val(ports["port_time"]["load_days"]),
        discharge_days=A.val(ports["port_time"]["discharge_days"]),
        charge_ballast_leg=charge_ballast_leg,
        canal_delay_days=A.val(ports["suez_canal"]["transit_delay_days"]),
        canal_toll_laden_usd=suez_toll_usd(vessel.suez_canal_net_tonnage, laden=True),
        canal_toll_ballast_usd=suez_toll_usd(vessel.suez_canal_net_tonnage, laden=False),
        war_risk_usd_per_transit=war_risk,
    )


def worldscale_freight_usd(points: float, flat_rate_usd_per_tonne: float, cargo_tonnes: float) -> float:
    """Freight from a Worldscale quote.

    Brokers quote tanker freight as a percentage ("points") of a published flat
    rate in dollars per tonne for the route. WS 100 means the flat rate itself;
    WS 150 means one and a half times it. Freight = points / 100 x flat rate x tonnes.
    """
    return points / 100 * flat_rate_usd_per_tonne * cargo_tonnes


def implied_tce(voyage_result: "VoyageResult", freight_usd: float) -> float:
    """The shipowner's daily earnings implied by a freight figure (time charter equivalent).

    Take what the cargo pays for freight, subtract everything the owner pays on
    the voyage other than the ship itself (fuel, ports, canal, war-risk cover),
    and divide by the days the ship is tied up. If the freight was built from a
    daily hire rate, this gives that hire rate back.
    """
    costs_other_than_hire = voyage_result.total_cost - voyage_result.costs["Vessel hire"]
    return (freight_usd - costs_other_than_hire) / voyage_result.total_days
