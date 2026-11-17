"""Landing page: what the tool does and how to read it."""

import streamlit as st

import ui
from engine import arbitrage
from engine import voyage as V

setup = st.session_state["setup"]
prices, _ = ui.get_prices()
inputs, dates = ui.base_inputs(setup, prices)
result = arbitrage.run(inputs)

st.title("Physical Crude Arbitrage & Voyage Engine")
st.markdown(
    "A physical oil trader asks one question every day: **if I buy a cargo of crude at port A and "
    "ship it to port B, do I make money today, and what drives the answer?** This tool works "
    "that out for US Gulf Coast and North Sea crude shipped to India, Europe or East Asia, and "
    "shows every step. "
    "The starting case is a one-million-barrel cargo to the west coast of India.")

st.subheader("Today's answer")
ui.verdict_banner(result)
c1, c2, c3, c4 = st.columns(4)
c1.metric("Buy at origin", ui.usd(result.purchase_price), help="The origin benchmark (WTI or Brent) plus the estimated differential for the grade shipped.")
c2.metric("Cost to deliver (estimated)", ui.usd(sum(result.cost_stack.values())),
          help="Freight, financing, insurance, transit loss and demurrage, per barrel. "
               "Built largely from estimates, above all the ship's daily hire rate.")
c3.metric("Sell at destination", ui.usd(result.sale_value),
          help=f"{dates['benchmark'].title()} plus an estimated quality adjustment.")
c4.metric("Margin per barrel", ui.usd(result.margin_per_bbl))
st.caption(f"{inputs.cargo_bbl / 1e6:.2f} million barrels, {V.get_port(inputs.origin_key)['name']} to "
           f"{V.get_port(inputs.destination_key)['name']}, {V.get_vessel(inputs.vessel_key).name}, "
           f"{ui.route_phrase(inputs.via)}. Prices: {dates['origin_name']} {dates['wti_label']}, "
           f"{dates['benchmark'].title()} {dates['destination_label']}. "
           "Change the trade in the sidebar on the left.")

st.subheader("How to read this tool")
a, b = st.columns(2)
a.markdown("""
**The idea in four lines**

1. Crude costs one price in the US and another at the discharge port.
2. Moving it costs money: a ship, fuel, canal tolls, interest, insurance.
3. If the price gap is bigger than the cost of moving it, the **arb is open** and the trade pays.
4. If not, the **arb is closed** and the oil stays where it is.

"Arb" is short for arbitrage: profiting from the same thing being priced differently in two places.
""")
b.markdown("""
**The pages**

- **Voyage calculator** - how long the trip takes and what the ship costs, Suez versus Cape.
- **Prices** - benchmark crude prices and the gap between them.
- **Arbitrage result** - every cost from purchase to sale, and the verdict.
- **Where to send it** - the same cargo costed to every discharge port and ranked by margin.
- **Scenarios & history** - sliders, what matters most, the break-even gap, and a look back.
- **Methodology** - every assumption, where it came from, and what the model leaves out.
""")

st.subheader("What is real and what is estimated")
st.markdown(f"""
- **Published data:** daily Brent and WTI prices (US Energy Information Administration), monthly
  Dubai (World Bank), the Suez Canal toll tariff and surcharges, the benchmark interest rate
  (SOFR), ship sizes and the quality of each crude grade.
- **Estimates, marked** {ui.ESTIMATED} **or "(estimated)":** the ship's daily hire rate (our own
  figure, or a public broker or press figure for another route or contract used as a stand-in),
  the fuel price, ship speeds and fuel use (reported from industry guides but not yet confirmed
  against the documents, or scaled from those figures), the ship's canal tonnage, port costs and
  port days, the bank's lending margin, insurance and war-risk cover, transit loss, the quality
  adjustment and the Gulf Coast price differential. Real freight rates and physical price premiums
  are sold by subscription and are not used here. The Methodology page lists every one.
- **Not a forecast.** The tool explains today's economics. It does not predict prices or give trading signals.
""")
