"""Methodology page: how the model works, every assumption, and its limits."""

import pandas as pd
import streamlit as st

from engine import assumptions as A

st.title("Methodology")
st.markdown("""
Everything on this dashboard comes from one piece of arithmetic:

> **margin = sale value at destination - (purchase price at origin + freight + financing + insurance + transit loss + demurrage)**

Each term is built from the assumptions listed below. No number is hidden in the code: every one
lives in a file under `data/assumptions/`, with its source and the date it was checked.
""")

st.subheader("How each number is calculated")
st.markdown("""
| Step | How it is worked out |
|---|---|
| **Distance and route** | Shortest sea path between the two ports from the open-source `searoute` library. If that path passes the Suez Canal the tool offers two routes: Suez, or the Cape (the same search with the canal forbidden, so the path goes round South Africa). If it does not (US Gulf to Europe) there is one direct route and no canal cost. The Panama Canal is never used. |
| **Voyage days** | Distance divided by speed, loaded and empty, plus days in port and a day for each canal transit. |
| **Vessel hire** | Days the ship is tied up (the full round trip) times the daily hire rate. |
| **Bunkers (fuel)** | Tonnes burned each day (at sea, in port, in the canal) times the fuel price. The fuel price is estimated from the latest daily Brent price. |
| **Canal tolls** | The Suez Canal Authority's published sliding-scale tariff applied to the ship's canal tonnage (an estimate), plus the current surcharge, converted from SDR to dollars. Charged loaded on the way out and empty on the way back. |
| **War-risk premium** | A percentage of the ship's value for each passage through the Red Sea. Suez route only. |
| **Freight per barrel** | All of the above plus port charges, divided by the barrels on board. |
| **Financing** | Cargo value x (benchmark interest rate + bank margin) x days financed / 360. |
| **Insurance** | A small percentage of cargo value plus freight, plus 10%. |
| **Transit loss** | A small percentage of the cargo, valued at the sale price. |
| **Quality adjustment** | (difference in API gravity x a dollar value per degree) minus (difference in sulphur x a dollar value per percentage point), comparing the grade shipped with the benchmark it is sold against. |
| **Demurrage** | Days of delay x (daily hire rate + fuel burned while waiting). |
| **Break-even spread** | The price gap at which the margin is zero, holding all costs fixed. |
""")

st.subheader("What this model does not do")
st.markdown("""
- **It does not use real traded freight or physical price data.** Actual freight rates (Baltic
  Exchange, Platts, Argus) and the premiums paid for physical cargoes are sold by subscription.
  This tool uses public benchmark prices and documented estimates, each labelled as such.
- **Freight is built bottom-up from a daily hire rate**, not from a quoted Worldscale or lump-sum
  rate. That makes the drivers visible, but the result depends heavily on the hire rate chosen.
- **The origin price is WTI at an inland hub plus an estimated differential**, not an actual
  Gulf Coast export price. The sale price is a benchmark plus a rule-of-thumb quality adjustment,
  not a negotiated delivered price.
- **The quality rule is a straight line.** Refiners value crude by the products it yields in their
  particular refinery, which a two-number rule cannot capture.
- **No hedging, no price movement during the voyage.** The cargo is bought and sold at today's
  prices. A real trader would hedge the weeks at sea with futures, and the shape of the futures
  curve (contango or backwardation) would add or subtract value.
- **No Panama Canal.** It is the shortest way from the US Gulf to China or Korea, but a VLCC
  cannot use it, a full Suezmax is at or beyond its draught limit, and we have no free source
  for the tanker toll. Cargoes to Asia are offered via Suez or the Cape only.
- **US crude only.** Every load port is on the US Gulf Coast and the grade is always WTI.
- **Simplified logistics.** No ship-to-ship transfers to load a VLCC, no brokerage commissions,
  no port congestion beyond the delay slider, no slow steaming to save fuel.
- **The historical view holds costs constant**, as explained on that chart.
- **Dubai is monthly only.** No free daily Dubai price exists, so with Dubai as the sell benchmark
  the tool compares monthly averages of Dubai and WTI, today and in the historical view. The fuel
  price still uses the latest daily Brent.
- **It does not forecast.** It explains today's economics.
""")

st.subheader("Every assumption")
table = pd.DataFrame(A.all_records())
only_estimates = st.toggle("Show estimates only")
files = st.multiselect("Files", sorted(table["file"].unique()), default=sorted(table["file"].unique()))
view = table[table["file"].isin(files)]
if only_estimates:
    view = view[view["estimate"]]
view = view.assign(value=view["value"].astype(str),
                   estimate=view["estimate"].map({True: "estimated", False: "published"}))
st.caption(f"{len(view)} assumptions shown; {int((table['estimate']).sum())} of {len(table)} in total are marked as estimates.")
st.dataframe(
    view.rename(columns={"file": "File", "assumption": "Assumption", "value": "Value", "unit": "Unit",
                         "estimate": "Status", "source": "Source", "url": "Link",
                         "checked": "Checked", "note": "Reasoning and limits"}),
    hide_index=True, width="stretch", height=600,
    column_config={"Link": st.column_config.LinkColumn(display_text="open")})
