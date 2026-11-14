"""Voyage calculator page: how long the trip takes and what it costs."""

import pandas as pd
import streamlit as st

import charts
import ui
from engine import assumptions as A
from engine import prices as P
from engine import voyage as V

setup = st.session_state["setup"]
prices, _ = ui.get_prices(st.session_state.get("refresh_count", 0))
vessel = V.get_vessel(setup["vessel_key"])
origin, destination = V.get_port(setup["origin"]), V.get_port(setup["destination"])
brent, _ = P.latest(prices, "brent")
bunker_default = P.bunker_price_estimate(brent)

st.title("Voyage calculator")
st.markdown(
    f"What it costs to move a cargo from **{origin['name']}** to **{destination['name']}** on a "
    f"**{vessel.name}**. The cargo pays for the ship for the whole round trip, including the "
    "empty leg home, plus fuel, port charges and canal tolls.")

left, right = st.columns(2)
hire = left.number_input("Ship hire, USD per day" + (" (estimated)" if setup["hire_is_estimate"] else ""),
                         value=float(setup["hire"]), step=5000.0, min_value=0.0,
                         help="Set by the Freight market choice in the sidebar. Change it here to test other levels.")
bunker = right.number_input("Fuel (bunker) price, USD per tonne (estimated)",
                            value=round(bunker_default), step=10, min_value=0,
                            help="Estimated as the Brent price times a fixed ratio. Real bunker prices are paywalled.")
cargo = vessel.cargo_capacity_bbl


def run(via: str) -> V.VoyageResult:
    return V.voyage_from_assumptions(setup["origin"], setup["destination"], setup["vessel_key"],
                                     via, hire_usd_per_day=hire, bunker_usd_per_tonne=bunker)


chosen = run(setup["via"])
other_via = "cape" if setup["via"] == "suez" else "suez"
other = run(other_via) if (other_via == "cape" or vessel.can_transit_suez_laden) else None

st.subheader(f"{V.ROUTES[setup['via']]}: the headline numbers")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Distance, one way", f"{chosen.distance_nm:,.0f} nm")
c2.metric("Days loaded (port to port)", f"{chosen.laden_days:,.1f}")
c3.metric("Days ship is tied up", f"{chosen.total_days:,.1f}", help="Round trip, including the empty leg home.")
c4.metric("Freight per barrel", ui.usd(chosen.cost_per_bbl),
          help=f"Total voyage cost {ui.usd(chosen.total_cost / 1e6, 2)} million over {cargo:,.0f} barrels.")

map_col, cost_col = st.columns([3, 2])
with map_col:
    routes = {V.ROUTES[setup["via"]]: V.sea_route(setup["origin"], setup["destination"], setup["via"])[1]}
    if other is not None:
        routes[V.ROUTES[other_via]] = V.sea_route(setup["origin"], setup["destination"], other_via)[1]
    st.plotly_chart(charts.route_map(routes, [origin, destination]), width="stretch")
with cost_col:
    st.markdown("**Where the freight cost comes from** (USD per barrel)")
    st.plotly_chart(charts.cost_bars(chosen.per_bbl()), width="stretch")
    biggest = max(chosen.costs, key=chosen.costs.get)
    st.caption(f"{biggest} is the biggest single cost: "
               f"{chosen.costs[biggest] / chosen.total_cost:.0%} of the voyage bill.")

if other is not None:
    st.subheader("Suez or Cape?")
    comparison = pd.DataFrame({
        V.ROUTES[v.via]: {
            "Distance, one way (nm)": f"{v.distance_nm:,.0f}",
            "Days loaded": f"{v.laden_days:,.1f}",
            "Days ship is tied up": f"{v.total_days:,.1f}",
            "Fuel burned (tonnes)": f"{v.total_fuel_tonnes:,.0f}",
            **{name: ui.usd(cost, 0) for name, cost in v.costs.items()},
            "Total voyage cost": ui.usd(v.total_cost, 0),
            "Freight per barrel": ui.usd(v.cost_per_bbl),
        } for v in (chosen, other)})
    st.table(comparison)
    cheaper, dearer = sorted((chosen, other), key=lambda v: v.cost_per_bbl)
    st.info(f"**{V.ROUTES[cheaper.via]}** is cheaper by {ui.usd(dearer.cost_per_bbl - cheaper.cost_per_bbl)} "
            f"a barrel at these rates. The Cape adds {abs(chosen.total_days - other.total_days):,.1f} days "
            "to the round trip, so the dearer the ship is per day, the more the canal toll is worth paying.")

with st.expander("Day-by-day and fuel detail"):
    labels = {"load_port": "Loading", "laden_sea": "At sea, loaded", "laden_canal": "Canal, loaded",
              "discharge_port": "Discharging", "ballast_sea": "At sea, empty", "ballast_canal": "Canal, empty"}
    st.table(pd.DataFrame({
        "Days": {labels[k]: f"{v:,.1f}" for k, v in chosen.days.items()},
        "Fuel burned (tonnes)": {labels[k]: f"{v:,.0f}" for k, v in chosen.fuel_tonnes.items()},
    }))

with st.expander("The ship and port assumptions behind these numbers"):
    raw = A.load("vessels")[setup["vessel_key"]]
    rows = [{"Assumption": key.replace("_", " "), "Value": A.val(node), "Unit": node.get("unit", ""),
             "Estimated?": "yes" if A.is_estimate(node) else "", "Source": node.get("source", "")}
            for key, node in raw.items() if "source" in node]
    st.dataframe(pd.DataFrame(rows).astype({"Value": str}), hide_index=True, width="stretch")
    st.caption("Port costs: " + ", ".join(
        f"{p['name']} {ui.usd(p['port_cost_usd'], 0)}" + (" (estimated)" if p["port_cost_is_estimate"] else "")
        for p in (origin, destination)) + ". Full list with links on the Methodology page.")
