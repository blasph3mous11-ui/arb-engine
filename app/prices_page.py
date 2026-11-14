"""Prices page: benchmark history and the gap between origin and destination."""

import pandas as pd
import streamlit as st

import charts
import ui
from engine import assumptions as A
from engine import prices as P

st.title("Prices")
st.markdown(
    "The trade starts with a price gap. We buy crude priced off **WTI** (the US benchmark) and "
    "sell it priced off **Brent** or **Dubai** (the benchmarks used for oil delivered to India). "
    "The gap between them has to pay for the whole voyage.")

if st.button("Download the latest prices", icon=":material/refresh:"):
    st.session_state["refresh_count"] = st.session_state.get("refresh_count", 0) + 1
prices, note = ui.get_prices(st.session_state.get("refresh_count", 0))
st.caption(f"{note} Sources: {P.SOURCES['brent']}; {P.SOURCES['wti']}; {P.SOURCES['dubai']}.")

benchmark = st.session_state["setup"]["benchmark"]
if benchmark == "dubai" and not prices["dubai"].notna().any():
    st.warning("Dubai prices could not be loaded, so Brent is used instead.")
    benchmark = "brent"

wti, wti_date = P.latest(prices, "wti")
brent, brent_date = P.latest(prices, "brent")
destination, destination_date = P.latest(prices, benchmark)
bunker = P.bunker_price_estimate(brent)
reference = A.record("market", "bunkers", "reference_houston_vlsfo_usd_per_tonne")

c1, c2, c3, c4 = st.columns(4)
c1.metric("WTI (origin)", ui.usd(wti), help=f"{P.SOURCES['wti']}, {wti_date:%d %b %Y}")
c2.metric("Brent", ui.usd(brent), help=f"{P.SOURCES['brent']}, {brent_date:%d %b %Y}")
c3.metric(f"Spread: {benchmark.title()} minus WTI", ui.usd(destination - wti),
          help="The gross price gap, before any costs.")
c4.metric("Ship fuel, per tonne (estimated)", ui.usd(bunker, 0),
          help=f"Brent x {A.get('market', 'bunkers', 'usd_per_tonne_per_brent_dollar')}. "
               f"Cross-check: {reference['source']} was ${A.val(reference)}.")
st.caption(f"Latest prices: WTI {wti_date:%d %b %Y}, Brent {brent_date:%d %b %Y}"
           + (f", Dubai monthly average for {destination_date:%B %Y}" if benchmark == "dubai" else "")
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

st.subheader(f"The spread: {benchmark.title()} minus WTI")
spread = (window[benchmark] - window["wti"]).dropna()
st.plotly_chart(charts.single_line(spread, "Spread", zero_label="no price gap"), width="stretch")
st.caption(f"Over this period the spread averaged {ui.usd(spread.mean())}, ranging from "
           f"{ui.usd(spread.min())} to {ui.usd(spread.max())}. Compare that with the freight "
           "cost per barrel on the Voyage page: the arb only opens when the spread, adjusted for "
           "quality, is bigger than all the costs.")

with st.expander("Why is the fuel price an estimate?"):
    record = A.record("market", "bunkers", "usd_per_tonne_per_brent_dollar")
    st.markdown(f"Port-by-port bunker prices come from paid services, so the tool estimates them: "
                f"**Brent x {A.val(record)}**.\n\n{record['note']}")

with st.expander("See the price table"):
    st.dataframe(window.sort_index(ascending=False).round(2), width="stretch")
