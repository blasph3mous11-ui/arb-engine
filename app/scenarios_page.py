"""Scenarios page: sliders, sensitivity (tornado), break-even and the historical view."""

import pandas as pd
import streamlit as st

import charts
import ui
from engine import arbitrage, scenarios
from engine import assumptions as A
from engine import voyage as V

setup = st.session_state["setup"]
prices, _ = ui.get_prices(st.session_state.get("refresh_count", 0))
base_inputs, dates = ui.base_inputs(setup, prices)
base = arbitrage.run(base_inputs)
benchmark_name = dates["benchmark"].title()
vessel = V.get_vessel(base_inputs.vessel_key)

st.title("Scenarios & history")
st.markdown("Move the main drivers and watch the margin respond. Nothing here is a forecast: "
            "each control simply re-runs today's arithmetic with one number changed.")

# ---------------------------------------------------------------- sliders
st.subheader("What if?")
left, right = st.columns(2)
hire = left.slider("Ship hire, USD per day", 10_000, 600_000, int(base_inputs.hire_usd_per_day), 5_000,
                   help="The daily cost of the ship. The biggest part of freight.")
bunker = left.slider("Fuel (bunker) price, USD per tonne", 200, 1_500,
                     int(round(base_inputs.bunker_usd_per_tonne)), 10)
rate = left.slider("Interest rate, % a year", 0.0, 15.0, float(base_inputs.interest_rate_pct), 0.25,
                   help="Benchmark rate (SOFR) plus the bank's margin.")
spread = right.slider(f"Price spread, {benchmark_name} minus WTI, USD per barrel", -10.0, 60.0,
                      float(round(base.benchmark_spread, 2)), 0.25,
                      help="Moves the destination price while holding WTI where it is.")
delay = right.slider("Delay at port, days", 0, 30, int(base_inputs.delay_days),
                     help="Days the ship waits beyond the agreed time. Charged as demurrage.")
can_use_suez = vessel.can_transit_suez_laden
suez_closed = right.toggle("Suez Canal closed (force the Cape route)", value=False, disabled=not can_use_suez,
                           help="Sends the ship round South Africa whatever the sidebar says.")

# The sliders work in whole dollars; if one has not been moved, keep the exact base value.
if bunker == int(round(base_inputs.bunker_usd_per_tonne)):
    bunker = base_inputs.bunker_usd_per_tonne
if spread == float(round(base.benchmark_spread, 2)):
    spread = base.benchmark_spread

scenario_inputs = base_inputs.with_changes(
    hire_usd_per_day=float(hire), bunker_usd_per_tonne=float(bunker), interest_rate_pct=rate,
    destination_benchmark_price=base_inputs.origin_benchmark_price + spread, delay_days=float(delay),
    via="cape" if (suez_closed or not can_use_suez) else base_inputs.via)
scenario = arbitrage.run(scenario_inputs)
breakeven = scenarios.breakeven_spread(scenario_inputs)

ui.verdict_banner(scenario)
c1, c2, c3, c4 = st.columns(4)
c1.metric("Margin per barrel", ui.usd(scenario.margin_per_bbl),
          delta=f"{scenario.margin_per_bbl - base.margin_per_bbl:+,.2f} vs today's base case")
c2.metric("Freight per barrel", ui.usd(scenario.cost_stack["Freight"]),
          delta=f"{scenario.cost_stack['Freight'] - base.cost_stack['Freight']:+,.2f}", delta_color="inverse")
c3.metric("Break-even spread", ui.usd(breakeven),
          help=f"The {benchmark_name}-minus-WTI gap at which the margin is exactly zero, at these costs.")
c4.metric("Spread in this scenario", ui.usd(spread),
          delta=f"{spread - breakeven:+,.2f} vs break-even")
st.caption(f"Break-even: with these costs the arb opens once {benchmark_name} is more than "
           f"{ui.usd(breakeven)} a barrel above WTI. Route: {V.ROUTES[scenario_inputs.via]}.")

# ---------------------------------------------------------------- tornado
st.subheader("Which input matters most?")
st.plotly_chart(charts.tornado(scenarios.tornado(scenario_inputs)), width="stretch")
st.caption("Each row changes one input and leaves the rest alone. The longer the bar, the more "
           "that input moves the margin. Blue is the input set lower, orange set higher. The sizes "
           "of the changes are our choice (listed on the Methodology page), so compare the rows "
           "with that in mind.")

# ---------------------------------------------------------------- history
st.subheader("Would past price gaps have paid, at these costs?")
years = st.radio("Period", [1, 2, 5], index=1, horizontal=True,
                 format_func=lambda y: f"{y} year" + ("s" if y > 1 else ""))
move_bunkers = st.checkbox("Let the fuel price follow Brent day by day", value=True,
                           help="Uses the same Brent ratio as the fuel estimate. If unticked, fuel "
                                "is held at the slider value.")


@st.cache_data(show_spinner="Re-running the model over past prices...")
def run_history(window: pd.DataFrame, inputs: arbitrage.ArbInputs, destination_column: str,
                ratio: float | None) -> pd.DataFrame:
    return scenarios.historical_run(window, inputs, "wti", destination_column, ratio)


window = prices[prices.index >= prices.index.max() - pd.DateOffset(years=years)]
ratio = A.get("market", "bunkers", "usd_per_tonne_per_brent_dollar") if move_bunkers else None
history = run_history(window, scenario_inputs, dates["benchmark"], ratio)

if history.empty:
    st.warning("No price history available for this period.")
else:
    st.plotly_chart(charts.history(history["margin"]), width="stretch")
    open_share = (history["margin"] > 0).mean()
    h1, h2, h3 = st.columns(3)
    h1.metric("Days the arb was open", f"{open_share:.0%}")
    h2.metric("Average margin", ui.usd(history["margin"].mean()))
    h3.metric("Best / worst day", f"{ui.usd(history['margin'].max())} / {ui.usd(history['margin'].min())}")
    st.warning(
        f"**Read this chart with care.** Only crude prices"
        f"{' and the fuel price' if move_bunkers else ''} change from day to day. The ship hire rate "
        f"({ui.usd(scenario_inputs.hire_usd_per_day, 0)} a day), canal tolls, interest rate, "
        "insurance and quality adjustment are all held at the values set above. In reality freight "
        "rates swing widely and tend to rise exactly when the price gap is wide, because everyone "
        "wants a ship at once. So this is not a record of what the trade actually earned. It "
        "answers a narrower question: how often was the price gap wide enough to cover "
        "*these* costs?", icon=":material/warning:")
