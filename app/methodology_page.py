"""Methodology page: how the model works, every assumption, and its limits."""

import pandas as pd
import streamlit as st

from engine import assumptions as A

st.title("Methodology")
st.markdown("""
Everything on this dashboard comes from one piece of arithmetic:

> **margin = sale value (benchmark + quality adjustment + futures curve effect) - (purchase price + freight + financing + insurance + transit loss + demurrage + reverse lightering + EU carbon)**

Each term is built from the assumptions listed below. No number is hidden in the code: every one
lives in a file under `data/assumptions/`, with its source and the date it was checked.
""")

st.subheader("How each number is calculated")
st.markdown("""
| Step | How it is worked out |
|---|---|
| **Distance and route** | Shortest sea path between the two ports from the open-source `searoute` library. If that path passes the Suez Canal the tool offers two routes: Suez, or the Cape (the same search with the canal forbidden, so the path goes round South Africa). If it does not (US Gulf or North Sea to Europe) there is one direct route and no canal cost. The Panama Canal is never used. |
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
| **Futures curve effect** | (second-month minus first-month futures price, typed in: WTI futures for US Gulf cargoes, Brent futures for North Sea cargoes) x days financed / 30. Positive in contango, negative in backwardation. |
| **Demurrage** | Days of delay x (daily hire rate + fuel burned while waiting). With a broker's quote, the quote's implied daily earnings replace the hire rate. |
| **Reverse lightering** | When a fully loaded ship is too deep for the load port's channel, the share of the cargo that cannot be loaded at the berth (from the ship's full and empty draught and the channel depth) x an estimated $1.00 per barrel loaded offshore, derived from a published 2018 range of 50-75 cents per barrel of a whole VLCC cargo. |
| **EU carbon (ETS)** | Fuel burned at berth in a scheme port (EU, Norway, Iceland) in full; fuel at sea in full between two scheme ports, half when one end is outside; x 3.114 t CO2 per tonne of fuel x coverage (100% from 2026) x the allowance price, in dollars. The UK is outside the EU scheme. |
| **Commissions** | With a broker's quote only: the charterer gets a 2.5% address commission back, and the owner pays it plus 1.25% brokerage, which lowers the owner's daily earnings. Both estimated. |
| **Break-even spread** | The price gap at which the margin is zero, holding all costs fixed. |
""")

st.subheader("What this model does not do")
st.markdown("""
- **It does not use real traded freight or physical price data.** Actual freight rates (Baltic
  Exchange, Platts, Argus) and the premiums paid for physical cargoes are sold by subscription.
  This tool uses public benchmark prices and documented estimates, each labelled as such.
- **Freight is built bottom-up from a daily hire rate** unless you type a broker's quote
  (Worldscale points and flat rate, or a lump sum) in the sidebar. The tool cannot supply real
  quotes or Worldscale flat rates, which are paywalled; it only does the arithmetic on the ones you
  enter, and shows what they pay the shipowner per day. Without a quote the result depends heavily
  on the hire rate chosen.
- **The origin price is WTI Cushing (US Gulf) or Brent (North Sea) plus an estimated
  differential**, not an actual export price. The sale price is a benchmark plus a quality
  adjustment, not a negotiated delivered price. When a cargo is bought and sold against the same
  benchmark it keeps its market differential; otherwise the adjustment is a gravity-and-sulphur
  rule of thumb, while the purchase differential is a dated market snapshot, so the two ends of a
  cross-benchmark trade do not come from the same source.
- **The quality rule is a straight line.** Refiners value crude by the products it yields in their
  particular refinery, which a two-number rule cannot capture.
- **The futures curve is a typed-in figure.** A hedged cargo gains or loses the curve's slope over
  the days at sea (shown as "futures curve effect" on the Arbitrage page). The free EIA futures
  data stopped in April 2024, so today's slope must be typed in; the tool does not model pricing
  windows, basis risk between WTI futures and the destination benchmark, or the cost of the hedge.
- **No Panama Canal.** It is the shortest way from the US Gulf to China or Korea, but a VLCC
  cannot use it, a full Suezmax is at or beyond its draught limit, and we have no free source
  for the tanker toll. Cargoes to Asia are offered via Suez or the Cape only.
- **Two load regions.** US Gulf Coast cargoes (WTI, WTI Midland, Mars) are bought at the free WTI
  Cushing price plus an estimated differential; North Sea cargoes (Forties from Hound Point, Johan
  Sverdrup from Mongstad) at the free Brent price, standing in for Dated Brent, plus an estimated
  differential. Real physical prices are paywalled. West African and Middle East origins are not
  offered because they would rest entirely on estimated prices. Crude is valued with a
  straight-line gravity-and-sulphur rule, not by the products a refinery would make from it:
  product yields per grade and product prices at destination are not available as free,
  consistent data.
- **Simplified logistics.** Reverse lightering is a flat rule of thumb per barrel, not a model of
  the top-up ships and days; commissions apply only to typed-in quotes; EU carbon uses a dated
  allowance price and ignores methane; no port congestion beyond the delay slider, no slow
  steaming to save fuel.
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
