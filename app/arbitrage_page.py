"""Arbitrage result page: the full cost stack and the open/closed verdict."""

import pandas as pd
import streamlit as st

import charts
import ui
from engine import arbitrage
from engine import assumptions as A
from engine import voyage as V

setup = st.session_state["setup"]
prices, _ = ui.get_prices()
inputs, dates = ui.base_inputs(setup, prices)
result = arbitrage.run(inputs)
vessel = V.get_vessel(inputs.vessel_key)
origin, destination = V.get_port(inputs.origin_key), V.get_port(inputs.destination_key)
benchmark_name = dates["benchmark"].title()

st.title("Arbitrage result")
st.markdown(
    f"Buy **{inputs.cargo_bbl / 1e6:.2f} million barrels** of WTI at {origin['name']}, ship it on a "
    f"{vessel.name} {V.ROUTES[inputs.via].replace('Via', 'via')} to {destination['name']}, and sell it against "
    f"{benchmark_name}. Does it pay today?")
ui.verdict_banner(result)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Purchase price", ui.usd(result.purchase_price),
          help=f"WTI {ui.usd(inputs.origin_benchmark_price)} ({dates['wti_label']}) "
               f"plus {ui.usd(inputs.origin_differential)} Gulf Coast differential (estimated).")
c2.metric("Landed cost", ui.usd(result.landed_cost), help="Purchase price plus every cost of delivery.")
c3.metric("Sale value", ui.usd(result.sale_value),
          help=f"{benchmark_name} {ui.usd(inputs.destination_benchmark_price)} "
               f"plus {ui.usd(result.quality_differential)} quality adjustment (estimated).")
c4.metric("Margin per barrel", ui.usd(result.margin_per_bbl))
if dates["monthly"]:
    st.caption(f"Dubai is only published as a monthly average, so the crude prices here are "
               f"{dates['month_label']} averages for both Dubai and WTI. The fuel price uses the "
               f"latest daily Brent ({dates['fuel_label']}).")

st.subheader("From purchase price to margin")
st.plotly_chart(charts.waterfall(result), width="stretch")
st.caption("Blue bars are price levels, orange bars are costs added on the way, and the green or "
           "red bar is what is left. The vertical axis does not start at zero, so that the cost "
           "steps are visible.")

st.subheader("Every line, explained")
financed_days = result.voyage.laden_days + inputs.delay_days + inputs.financing_extra_days
E = " (estimated)"
sofr, bank_margin = A.get("costs", "financing", "benchmark_rate_pct"), A.get("costs", "financing", "margin_pct")
lines = [
    ("WTI benchmark price", inputs.origin_benchmark_price,
     f"EIA spot price for WTI at Cushing, {dates['wti_label']}."),
    ("+ Gulf Coast differential" + E, inputs.origin_differential,
     "Oil on a ship at the coast costs a little more than oil at the inland hub."),
    ("= Purchase price", result.purchase_price, "What we pay per barrel at the load port."),
    # Freight always contains estimates (the fuel price at least), whatever the hire rate's status.
    ("+ Freight" + (E if setup["hire_is_estimate"] else " (part estimated)"), result.cost_stack["Freight"],
     f"{result.voyage.total_days:.1f} days of ship hire at {ui.usd(inputs.hire_usd_per_day, 0)} a day"
     f"{E if setup['hire_is_estimate'] else ''}, "
     f"{result.voyage.total_fuel_tonnes:,.0f} tonnes of fuel at {ui.usd(inputs.bunker_usd_per_tonne, 0)} "
     "(estimated), port charges, canal tolls. See the Voyage page."),
    ("+ Financing (part estimated)", result.cost_stack["Financing"],
     f"SOFR {sofr:.2f}% plus an estimated {bank_margin:.2f}% bank margin = {inputs.interest_rate_pct:.2f}% "
     f"a year on the cargo value for {financed_days:.1f} days."),
    ("+ Insurance" + E, result.cost_stack["Insurance"],
     f"{inputs.insurance_rate_pct}% of cargo value plus freight, plus 10%."),
    ("+ Transit loss" + E, result.cost_stack["Transit loss"],
     f"{inputs.transit_loss_pct}% of the oil loaded is not there to sell at discharge."),
    ("+ Demurrage" + E, result.cost_stack["Demurrage"],
     f"{inputs.delay_days:.0f} days of delay, charged at the daily hire rate plus fuel burned while "
     "waiting. Add delay days on the Scenarios page."),
    ("= Landed cost", result.landed_cost, "Total cost of a barrel delivered to the buyer."),
    (f"{benchmark_name} benchmark price", inputs.destination_benchmark_price,
     f"Latest available, {dates['destination_label']}."),
    ("+ Quality adjustment" + E, result.quality_differential,
     f"WTI is lighter and lower in sulphur than {benchmark_name}, so it is worth a little more."),
    ("+ Destination differential" + E, inputs.destination_differential,
     "Any premium the buyer pays over the benchmark. Unknown without paid data, so zero."),
    ("= Sale value", result.sale_value, "What a barrel is worth delivered."),
    ("MARGIN (sale value minus landed cost)", result.margin_per_bbl,
     "Positive: the arb is open. Negative: it is closed."),
]
table = pd.DataFrame(lines, columns=["Line", "USD per barrel", "Where it comes from"])
table["USD on the cargo"] = (table["USD per barrel"] * inputs.cargo_bbl).map(lambda v: ui.usd(v, 0))
table["USD per barrel"] = table["USD per barrel"].map(ui.usd)
st.dataframe(table[["Line", "USD per barrel", "USD on the cargo", "Where it comes from"]],
             hide_index=True, width="stretch", height=38 * (len(lines) + 1))

costs = sum(result.cost_stack.values())
freight_share = result.cost_stack["Freight"] / costs
# The gap after the price adjustments. Adjusted gap minus costs is exactly the margin,
# so this sentence can never disagree with the verdict at the top of the page.
price_adjustments = (result.quality_differential + inputs.destination_differential
                     - inputs.origin_differential)
adjusted_gap = result.benchmark_spread + price_adjustments
st.info(
    f"**How to read this.** The price gap between {benchmark_name} and WTI is "
    f"{ui.usd(result.benchmark_spread)} a barrel. After the estimated quality adjustment "
    f"({result.quality_differential:+.2f}), the estimated destination differential "
    f"({inputs.destination_differential:+.2f}) and the estimated Gulf Coast differential "
    f"({-inputs.origin_differential:+.2f}), the gap is worth {ui.usd(adjusted_gap)}. "
    f"Getting the oil to India costs an estimated {ui.usd(costs)} a barrel, of which freight is "
    f"{freight_share:.0%}. "
    + ("The adjusted gap is wide enough to cover it." if result.is_open else
       "The adjusted gap is not wide enough to cover it, so nobody would ship this cargo on these "
       "terms: either the US price must fall, the price in India must rise, or freight must get cheaper.")
    + " Try the other freight markets in the sidebar to see how much the answer depends on the ship.")

st.caption("Real delivered prices and freight rates are negotiated privately and published only by "
           "paid services. This page uses public benchmark prices and the documented estimates "
           "listed on the Methodology page.")
