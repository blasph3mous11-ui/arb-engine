"""Where to send it: the same cargo costed to every discharge port, ranked by margin."""

import pandas as pd
import streamlit as st

import charts
import ui
from engine import assumptions as A
from engine import ranking
from engine import voyage as V

setup = st.session_state["setup"]
prices, _ = ui.get_prices()
inputs, dates = ui.base_inputs(setup, prices)
vessel = V.get_vessel(inputs.vessel_key)
origin = V.get_port(inputs.origin_key)
benchmark_name = dates["benchmark"].title()

st.title("Where to send it")
st.markdown(
    f"A trader with a cargo to place compares every destination by what is left after all "
    f"costs. This page takes **{inputs.cargo_bbl / 1e6:.2f} million barrels** of "
    f"{A.val(A.load('costs')['grades'][inputs.grade]['name']).split(' (')[0]} loaded at "
    f"**{origin['name']}** on {ui.a_or_an(vessel.name)} and works out the margin to each "
    f"discharge port, using the cheapest route available to that port.")

if inputs.freight_override_usd is not None:
    st.info("A broker's quote covers one voyage only, so this ranking costs every destination from "
            "the daily hire rate in the freight market chosen in the sidebar.")
    inputs = inputs.with_changes(freight_override_usd=None)
rows = ranking.rank_destinations(inputs)
best, worst = rows[0], rows[-1]

if best["margin"] > 0:
    st.success(f"### Best destination today: {best['port']}\n"
               f"Margin {ui.usd(best['margin'])} a barrel, {ui.route_phrase(best['via'])}.",
               icon=":material/check_circle:")
else:
    st.error(f"### No destination pays today\n"
             f"The least bad is {best['port']}, losing {ui.usd(abs(best['margin']))} a barrel "
             f"{ui.route_phrase(best['via'])}.", icon=":material/cancel:")

st.subheader("Margin by destination (estimated)")
st.plotly_chart(charts.ranking_bars(rows), width="stretch")
st.caption(
    f"Every port is valued against the same price, {benchmark_name} ({dates['destination_label']}) "
    "plus the estimated quality adjustment, so the differences between ports come only from the "
    "voyage: distance, days, canal tolls and port costs. In reality each market pays its own "
    "premium or discount, which is negotiated privately and not available as free data.")

st.subheader("The numbers behind the ranking")
table = pd.DataFrame([{
    "Destination": r["port"],
    "Route": V.ROUTES[r["via"]],
    "Distance (nm)": f"{r['distance_nm']:,.0f}",
    "Days loaded": f"{r['days_loaded']:,.1f}",
    "Freight (estimated)": ui.usd(r["freight"]),
    "Other costs": ui.usd(r["other_costs"]),
    "Landed cost": ui.usd(r["landed_cost"]),
    "Sale value": ui.usd(r["sale_value"]),
    "Margin per barrel": ui.usd(r["margin"]),
    "Margin on the cargo": ui.usd(r["margin_total_usd"], 0),
} for r in rows])
st.dataframe(table, hide_index=True, width="stretch")
st.caption("Freight is built from the ship's daily hire rate in the freight market chosen in the "
           "sidebar, and the fuel price is estimated from Brent. Other costs are financing, "
           "insurance, transit loss and demurrage. All in USD per barrel loaded.")

gap = best["margin"] - worst["margin"]
st.info(
    f"**How to read this.** {best['port']} comes out best: {best['distance_nm']:,.0f} nautical "
    f"miles and {best['days_loaded']:,.0f} days loaded, for freight of {ui.usd(best['freight'])} "
    f"a barrel. {worst['port']} comes out worst, with freight of {ui.usd(worst['freight'])} a "
    f"barrel over {worst['distance_nm']:,.0f} miles. That is a gap of "
    f"{ui.usd(gap)} a barrel between the best and worst destination, so the further market would "
    f"have to pay at least that much more for the same oil before it became the better home. "
    "Try a different ship or freight market in the sidebar: the dearer the ship, the more "
    "distance matters.")
