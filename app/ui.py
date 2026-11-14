"""Shared dashboard pieces: the sidebar where the trade is chosen, and small helpers.

No calculations here. This file collects the user's choices and hands them to engine/.
"""

import streamlit as st

from engine import arbitrage
from engine import assumptions as A
from engine import prices as P
from engine import voyage as V

BENCHMARK_LABELS = {"brent": "Brent (daily)", "dubai": "Dubai (monthly average)"}
ESTIMATED = ":orange-badge[estimated]"


@st.cache_data(ttl=3600, show_spinner="Loading crude prices...")
def get_prices(refresh_count: int = 0):
    """Benchmark prices and a note on their origin. Re-downloads when refresh_count changes."""
    return P.load_benchmarks(refresh=refresh_count > 0)


def usd(value: float, decimals: int = 2) -> str:
    sign = "-" if value < 0 else ""
    return f"{sign}${abs(value):,.{decimals}f}"


def tag(is_estimate: bool) -> str:
    """Badge shown next to any figure that is our estimate rather than a published number."""
    return f" {ESTIMATED}" if is_estimate else ""


def sidebar_setup() -> dict:
    """Draw the trade selector and return the choices."""
    sb = st.sidebar
    sb.header("The trade")
    origin = sb.selectbox("Load port", V.port_keys("origin"),
                          format_func=lambda k: V.get_port(k)["name"], key="origin")
    destination = sb.selectbox("Discharge port", V.port_keys("destination"),
                               format_func=lambda k: V.get_port(k)["name"], key="destination")
    vessels = V.vessel_keys()
    vessel_key = sb.selectbox(
        "Ship", vessels, index=vessels.index("suezmax"), key="vessel",
        format_func=lambda k: f"{V.get_vessel(k).name} "
                              f"({V.get_vessel(k).cargo_capacity_bbl / 1e6:.2f}m barrels)")
    vessel = V.get_vessel(vessel_key)

    if vessel.can_transit_suez_laden:
        via = sb.radio("Route", list(V.ROUTES), format_func=V.ROUTES.get, key="via")
    else:
        via = "cape"
        sb.info(f"A fully laden {vessel.name} is too deep for the Suez Canal, so it goes via the Cape.")

    markets = A.load("market")["freight_markets"]
    market_keys = list(markets)
    market = sb.selectbox(
        "Freight market", market_keys, key="market",
        index=market_keys.index(A.get("market", "default_freight_market")),
        format_func=lambda k: A.val(markets[k]["label"]),
        help="How much the ship costs to hire per day. Real freight rates are paywalled; "
             "these are public broker and press figures.")
    hire_record = markets[market]["hire_usd_per_day"][vessel_key]
    sb.caption(f"{A.val(markets[market]['description'])}  \n**Hire: {usd(A.val(hire_record), 0)} a day**"
               f"{tag(A.is_estimate(hire_record))}")

    benchmark = sb.selectbox("Sell price benchmark", list(BENCHMARK_LABELS),
                             format_func=BENCHMARK_LABELS.get, key="benchmark",
                             help="The published price the cargo is valued against in India.")
    return dict(origin=origin, destination=destination, vessel_key=vessel_key, via=via,
                market=market, hire=A.val(hire_record), hire_is_estimate=A.is_estimate(hire_record),
                benchmark=benchmark)


def base_inputs(setup: dict, prices) -> tuple[arbitrage.ArbInputs, dict]:
    """Today's trade: the sidebar choices plus the latest prices. Also returns the price dates."""
    wti, wti_date = P.latest(prices, "wti")
    brent, brent_date = P.latest(prices, "brent")
    benchmark = setup["benchmark"]
    monthly = benchmark == "dubai" and prices["dubai"].notna().any()
    if monthly:
        # Dubai is only published as a monthly average, so compare like with like:
        # use the WTI and Brent averages for that same month.
        destination_price, destination_date = P.latest(prices, "dubai")
        month = prices[prices.index.to_period("M") == destination_date.to_period("M")]
        wti, brent = float(month["wti"].mean()), float(month["brent"].mean())
        wti_date = brent_date = destination_date
    else:
        benchmark, destination_price, destination_date = "brent", brent, brent_date
    inputs = arbitrage.default_inputs(
        origin_benchmark_price=wti, destination_benchmark_price=destination_price,
        bunker_usd_per_tonne=P.bunker_price_estimate(brent),
        origin_key=setup["origin"], destination_key=setup["destination"],
        vessel_key=setup["vessel_key"], via=setup["via"], destination_benchmark=benchmark,
        hire_usd_per_day=setup["hire"],
    )
    date_format = "%B %Y average" if monthly else "%d %b %Y"
    dates = dict(wti=wti_date, brent=brent_date, destination=destination_date,
                 brent_price=brent, benchmark=benchmark, monthly=monthly,
                 wti_label=f"{wti_date:{date_format}}", destination_label=f"{destination_date:{date_format}}")
    return inputs, dates


def verdict_banner(result) -> None:
    """The headline: is the arb open or closed, and by how much."""
    line = (f"{usd(result.margin_per_bbl)} per barrel, "
            f"{usd(result.margin_total_usd / 1e6, 1)} million on the cargo")
    if result.is_open:
        st.success(f"### ARB OPEN\nShipping this cargo makes {line}.", icon=":material/check_circle:")
    else:
        st.error(f"### ARB CLOSED\nShipping this cargo loses {line.replace('-', '')}.",
                 icon=":material/cancel:")
