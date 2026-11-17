"""Prices page: benchmark history and the gap between origin and destination."""

import pandas as pd
import streamlit as st

import charts
import ui
from engine import assumptions as A
from engine import prices as P

st.title("Prices")
st.markdown(
    "The trade starts with a price gap. We buy crude priced off **WTI** (US Gulf cargoes) or "
    "**Brent** (North Sea cargoes) and "
    "sell it priced off **Brent** or **Dubai** (the benchmarks used for oil delivered to Europe "
    "and Asia). "
    "The gap between them has to pay for the whole voyage.")

if st.button("Download the latest prices", icon=":material/refresh:"):
    # Download now, then empty the copy held in memory so every page reads the new file.
    _, note = P.load_benchmarks(refresh=True)
    ui.get_prices.clear()
    prices, _ = ui.get_prices()
else:
    prices, note = ui.get_prices()
st.caption(f"{note} Sources: {P.SOURCES['brent']}; {P.SOURCES['wti']}; {P.SOURCES['dubai']}.")

# The same base case as the Arbitrage and Scenarios pages, so the spread and fuel price agree.
inputs, dates = ui.base_inputs(st.session_state["setup"], prices)
benchmark, monthly = dates["benchmark"], dates["monthly"]
if st.session_state["setup"]["benchmark"] == "dubai" and not monthly:
    st.warning("Dubai prices could not be loaded, so Brent is used instead.")

origin_column = dates["origin_column"]
wti, wti_date = P.latest(prices, origin_column)
brent, brent_date = P.latest(prices, "brent")
spread_today = inputs.destination_benchmark_price - inputs.origin_benchmark_price
reference = A.record("market", "bunkers", "reference_houston_vlsfo_usd_per_tonne")

c1, c2, c3, c4 = st.columns(4)
c1.metric(f"{dates['origin_name']} (origin)", ui.usd(wti), help=f"{P.SOURCES[origin_column]}, {wti_date:%d %b %Y}")
c2.metric("Brent", ui.usd(brent), help=f"{P.SOURCES['brent']}, {brent_date:%d %b %Y}")
c3.metric(f"Spread: {benchmark.title()} minus {dates['origin_name']}"
          + (f" ({dates['month_label']} averages)" if monthly else ""), ui.usd(spread_today),
          help=f"The gross price gap, before any costs: {benchmark.title()} "
               f"{ui.usd(inputs.destination_benchmark_price)} ({dates['destination_label']}) minus {dates['origin_name']} "
               f"{ui.usd(inputs.origin_benchmark_price)} ({dates['wti_label']}).")
c4.metric("Ship fuel, per tonne (estimated)", ui.usd(inputs.bunker_usd_per_tonne, 0),
          help=f"Latest daily Brent x {A.get('market', 'bunkers', 'usd_per_tonne_per_brent_dollar')}. "
               f"Cross-check: {reference['source']} was ${A.val(reference)}.")
st.caption(f"Latest prices: WTI {wti_date:%d %b %Y}, Brent {brent_date:%d %b %Y}"
           + (f". Dubai is only published as a monthly average (latest: {dates['month_label']}), so the "
              f"spread above compares the Dubai and {dates['origin_name']} averages for that month, not today's {dates['origin_name']}"
              if monthly else "")
           + ". These are spot prices published by the EIA a few days in arrears, so they can differ "
             "from futures prices quoted in the news.")

years = st.radio("History to show", [1, 2, 5, 10], index=1, horizontal=True,
                 format_func=lambda y: f"{y} year" + ("s" if y > 1 else ""))
window = prices[prices.index >= prices.index.max() - pd.DateOffset(years=years)]

st.subheader("Benchmark prices")
columns = {"wti": "WTI", "brent": "Brent"}
if window["dubai"].notna().any():
    columns["dubai"] = "Dubai (monthly average)"
st.plotly_chart(charts.price_lines(window, columns), width="stretch")

st.subheader(f"The spread: {benchmark.title()} minus {dates['origin_name']}")
# Daily prices for Brent; monthly averages for Dubai, so month is compared with month.
spread_window = ui.history_window(prices, years, monthly)
spread = (spread_window[benchmark] - spread_window[origin_column]).dropna()
st.plotly_chart(charts.single_line(spread, "Spread", zero_label="no price gap"), width="stretch")
st.caption(("Dubai is published only as a monthly average, so each point is one month: the "
            f"month's average Dubai price minus the month's average {dates['origin_name']} price. " if monthly else "")
           + f"Over this period the spread averaged {ui.usd(spread.mean())}, ranging from "
           f"{ui.usd(spread.min())} to {ui.usd(spread.max())}. Compare that with the estimated freight "
           "cost per barrel on the Voyage page: the arb only opens when the spread, adjusted for "
           "quality, is bigger than all the costs.")

with st.expander("Why is the fuel price an estimate?"):
    record = A.record("market", "bunkers", "usd_per_tonne_per_brent_dollar")
    st.markdown(f"Port-by-port bunker prices come from paid services, so the tool estimates them: "
                f"**Brent x {A.val(record)}**.\n\n{record['note']}")

with st.expander("See the price table"):
    st.dataframe(window.sort_index(ascending=False).round(2), width="stretch")
