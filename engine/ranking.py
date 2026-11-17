"""Where should this cargo go?

A trader with one cargo to place compares every possible destination by what
is left after all costs (the "netback" view). This module runs the same
arbitrage arithmetic once per discharge port and ranks the results.
"""

from engine import voyage
from engine.arbitrage import ArbInputs, ArbResult, run


def best_route_result(inputs: ArbInputs, destination_key: str) -> ArbResult:
    """The trade to one destination by its better available route.

    Where both Suez and the Cape exist we cost both and keep whichever leaves the
    higher margin, as a trader would. That is usually the cheaper voyage, but in a
    steep contango the longer voyage can earn more from the futures curve.
    """
    options = voyage.route_options(inputs.origin_key, destination_key, inputs.vessel_key)
    results = [run(inputs.with_changes(destination_key=destination_key, via=via)) for via in options]
    return max(results, key=lambda result: result.margin_per_bbl)


def rank_destinations(inputs: ArbInputs) -> list[dict]:
    """One row per discharge port, best margin first.

    Every port is valued against the same sell-price benchmark (the one in
    `inputs`), so the ranking compares like with like: the differences come
    from the voyage, not from mixing price references.
    """
    rows = []
    for key in voyage.port_keys("destination"):
        result = best_route_result(inputs, key)
        port = voyage.get_port(key)
        rows.append({
            "key": key,
            "port": port["name"],
            "region": port["region"],
            "via": result.voyage.via,
            "distance_nm": result.voyage.distance_nm,
            "days_loaded": result.voyage.laden_days,
            "freight": result.cost_stack["Freight"],
            "other_costs": sum(result.cost_stack.values()) - result.cost_stack["Freight"],
            "landed_cost": result.landed_cost,
            "sale_value": result.sale_value,
            "margin": result.margin_per_bbl,
            "margin_total_usd": result.margin_total_usd,
        })
    return sorted(rows, key=lambda row: row["margin"], reverse=True)
