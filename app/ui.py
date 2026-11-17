"""Shared dashboard pieces: the sidebar where the trade is chosen, and small helpers.

No calculations here. This file collects the user's choices and hands them to engine/.
"""

import pandas as pd
import streamlit as st

from engine import arbitrage
from engine import assumptions as A
from engine import prices as P
from engine import voyage as V

ORIGIN_BENCHMARK_LABELS = {"wti": "WTI Cushing", "brent": "Dated Brent"}
FREIGHT_BASES = {
    "hire": "Daily hire rate (from the freight market)",
    "worldscale": "Broker quote: Worldscale",
    "lump_sum": "Broker quote: lump sum",
}
BENCHMARK_LABELS = {"brent": "Brent (daily)", "dubai": "Dubai (monthly average)"}
ESTIMATED = ":orange-badge[estimated]"


@st.cache_data(ttl=3600, show_spinner="Loading crude prices...")
def get_prices():
    """Benchmark prices and a note saying when they were downloaded.

    Held in memory for an hour and shared by every visitor. The Prices page
    button downloads a new file and then empties this memory (get_prices.clear()).
    """
    return P.load_benchmarks()


def usd(value: float, decimals: int = 2) -> str:
    sign = "-" if value < 0 else ""
    return f"{sign}${abs(value):,.{decimals}f}"


def route_phrase(via: str) -> str:
    """The route as it reads in a sentence: 'via Suez Canal', 'by the direct route (no canal)'."""
    if via == "direct":
        return "by the direct route (no canal)"
    return V.ROUTES[via].replace("Via", "via")


def a_or_an(name: str) -> str:
    """'an Aframax', 'a Suezmax'."""
    return ("an " if name[0].upper() in "AEIOU" else "a ") + name


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
    grades = A.load("costs")["grades"]
    # Each load region has its own grades and its own price benchmark (WTI or Brent).
    region = V.get_port(origin)["region"]
    benchmark_label = ORIGIN_BENCHMARK_LABELS[arbitrage.origin_benchmark(origin)]
    grade_options = arbitrage.shipped_grades(origin_key=origin)
    # One remembered choice per region where every port offers the same grades (the US Gulf),
    # otherwise one per terminal (each North Sea blend loads at its own terminal).
    grade_key = f"grade_{region}" if grade_options == arbitrage.shipped_grades(region) else f"grade_{origin}"
    grade = sb.selectbox("Crude grade shipped", grade_options, key=grade_key,
                         format_func=lambda k: A.val(grades[k]["name"]),
                         help=f"Grades loaded at this port, each bought against {benchmark_label} "
                              "plus a differential.")
    origin_differential = sb.number_input(
        f"Differential to {benchmark_label}, USD per barrel (estimated)", step=0.05, format="%.2f",
        value=float(arbitrage.export_differential(grade)), key=f"origin_differential_{grade}",
        help=f"What this grade costs on a ship over the free {benchmark_label} price. Real "
             "physical prices are paywalled; the starting figure is a dated estimate listed on the "
             "Methodology page. In 2026 these swung by several dollars within weeks.")
    warning = V.draught_warning(origin, vessel_key)
    if warning:
        sb.warning(warning, icon=":material/water:")

    # Only offer the routes that really exist for these ports and this ship.
    options = V.route_options(origin, destination, vessel_key)
    if len(options) > 1:
        via = sb.radio("Route", options, format_func=V.ROUTES.get, key="via")
    elif options == ["direct"]:
        via = "direct"
        sb.info("Route: direct. This voyage does not go near the Suez Canal, so there is no canal "
                "toll and no Suez-or-Cape choice.")
    else:
        via = "cape"
        sb.info(f"A fully laden {vessel.name} is too deep for the Suez Canal, so it goes via the Cape.")

    markets = A.load("market")["freight_markets"]
    market_keys = list(markets)
    market = sb.selectbox(
        "Freight market", market_keys, key="market",
        index=market_keys.index(A.get("market", "default_freight_market")),
        format_func=lambda k: A.val(markets[k]["label"]),
        help="How much the ship costs to hire per day. Real freight rates for this route are "
             "paywalled, so every figure here is an estimate: either a public broker or press "
             "figure for another route or contract used as a stand-in, or our own estimate.")
    hire_record = markets[market]["hire_usd_per_day"][vessel_key]
    sb.caption(f"{A.val(markets[market]['description'])}  \n**Hire: {usd(A.val(hire_record), 0)} a day**"
               f"{tag(A.is_estimate(hire_record))}")

    basis = sb.radio("How is freight set?", list(FREIGHT_BASES), format_func=FREIGHT_BASES.get,
                     key="freight_basis",
                     help="Brokers quote tanker freight either in Worldscale points or as a lump sum "
                          "for the voyage. Type a quote here to use it instead of the daily hire rate.")
    quote_usd = None
    if basis != "hire":
        quote_usd = _freight_quote_inputs(sb, basis, origin, destination, vessel_key, via,
                                          A.val(hire_record), grade)

    with sb.expander("Hedging: the futures curve"):
        curve = st.number_input(
            "Second month minus first month futures, USD per barrel",
            value=float(A.get("costs", "futures_curve", "default_m2_minus_m1_usd_per_bbl")),
            step=0.05, format="%.2f", key="curve_m2_minus_m1",
            help="Positive: later months dearer (contango), which helps a hedged cargo. Negative: "
                 "backwardation, which hurts it. Use WTI futures for US crude and Brent futures "
                 "for North Sea crude. The free US EIA futures data stopped in April 2024, so type "
                 "today's figure from a futures quote. Zero means no effect.")
        st.caption("The Arbitrage page shows the 1985-2024 history for scale.")

    benchmark = sb.selectbox("Sell price benchmark", list(BENCHMARK_LABELS),
                             format_func=BENCHMARK_LABELS.get, key="benchmark",
                             help="The published price the cargo is valued against at the discharge port. Brent is "
                                  "the usual reference in Europe; India and East Asia use both Brent and Dubai.")
    return dict(origin=origin, destination=destination, vessel_key=vessel_key, via=via,
                market=market, hire=A.val(hire_record), hire_is_estimate=A.is_estimate(hire_record),
                benchmark=benchmark, freight_basis=basis, freight_quote_usd=quote_usd,
                curve_m2_minus_m1=curve, grade=grade, origin_differential=origin_differential)


def _freight_quote_inputs(sb, basis, origin, destination, vessel_key, via, hire, grade) -> float:
    """Boxes for a broker's freight quote. Returns the quoted freight for the whole cargo, in USD.

    The boxes start at the figure the daily hire rate gives for this exact voyage, so
    switching on a quote changes nothing until a broker's numbers are typed in.
    """
    prices, _ = get_prices()
    brent, _ = P.latest(prices, "brent")
    built_up = V.voyage_from_assumptions(origin, destination, vessel_key, via, hire_usd_per_day=hire,
                                         bunker_usd_per_tonne=P.bunker_price_estimate(brent)).total_cost
    # Quotes are gross of the address commission the charterer gets back, so the pre-fill is
    # grossed up: net of commission it equals the daily-hire freight for this voyage.
    address_pct = A.get("costs", "commissions", "address_commission_pct")
    gross = built_up / (1 - address_pct / 100)
    voyage_key = f"{origin}_{destination}_{vessel_key}_{via}_{grade}"
    if basis == "lump_sum":
        millions = sb.number_input("Lump sum for the voyage, USD million", min_value=0.0, step=0.1,
                                   value=round(gross / 1e6, 2), key=f"lump_{voyage_key}",
                                   help="The total freight the broker quotes for this voyage.")
        sb.caption("Pre-filled so that, after the address commission, it matches the daily-hire "
                   "estimate for this voyage. Type the broker's figure.")
        return millions * 1e6
    tonnes = arbitrage.cargo_tonnes(V.get_vessel(vessel_key).cargo_capacity_bbl, grade)
    points = sb.number_input("Worldscale points", min_value=0.0, step=5.0, value=100.0,
                             key=f"ws_points_{voyage_key}",
                             help="The percentage of the flat rate the broker quotes: WS 150 means 1.5 x.")
    flat = sb.number_input("Flat rate for the route, USD per tonne", min_value=0.0, step=0.5,
                           value=round(gross / tonnes, 2), key=f"ws_flat_{voyage_key}",
                           help="Published each year by the Worldscale Association (subscription only).")
    sb.caption(f"Pre-filled so that WS 100, after the address commission, matches the daily-hire "
               f"estimate for this voyage "
               f"({tonnes:,.0f} tonnes of {A.val(A.load('costs')['grades'][grade]['name']).split(' (')[0]}). "
               "Type the broker's points and the route's flat rate. "
               "The real flat rates are paywalled, so the tool does not guess them.")
    return V.worldscale_freight_usd(points, flat, tonnes)


def base_inputs(setup: dict, prices) -> tuple[arbitrage.ArbInputs, dict]:
    """Today's trade: the sidebar choices plus the latest prices. Also returns the price dates.

    Every page builds its base case here, so they all show the same numbers.
    """
    # The price the cargo is bought against depends on where it loads: WTI or Brent.
    origin_column = arbitrage.origin_benchmark(setup["origin"])
    wti, wti_date = P.latest(prices, origin_column)
    brent, brent_date = P.latest(prices, "brent")
    benchmark = setup["benchmark"]
    monthly = benchmark == "dubai" and prices["dubai"].notna().any()
    if monthly:
        # Dubai is only published as a monthly average, so compare like with like:
        # the latest month that has a Dubai price, against the origin benchmark's average for that month.
        month = P.monthly_averages(prices, origin_column=origin_column).iloc[-1]
        wti, destination_price = float(month[origin_column]), float(month["dubai"])
        wti_date = destination_date = month.name
    else:
        benchmark, destination_price, destination_date = "brent", brent, brent_date
    inputs = arbitrage.default_inputs(
        origin_benchmark_price=wti, destination_benchmark_price=destination_price,
        # Fuel is bought at today's price whichever crude benchmark is chosen,
        # so the fuel estimate always uses the latest daily Brent.
        bunker_usd_per_tonne=P.bunker_price_estimate(brent),
        origin_key=setup["origin"], destination_key=setup["destination"],
        vessel_key=setup["vessel_key"], via=setup["via"], destination_benchmark=benchmark,
        hire_usd_per_day=setup["hire"],
        freight_override_usd=setup.get("freight_quote_usd"),
        curve_m2_minus_m1=setup.get("curve_m2_minus_m1", 0.0),
        grade=setup.get("grade", "wti"), origin_differential=setup.get("origin_differential", 1.0),
        origin_benchmark=origin_column,
    )
    date_format = "%B %Y average" if monthly else "%d %b %Y"
    dates = dict(wti=wti_date, brent=brent_date, destination=destination_date,
                 origin_column=origin_column, origin_name="WTI" if origin_column == "wti" else "Brent",
                 benchmark=benchmark, monthly=monthly,
                 wti_label=f"{wti_date:{date_format}}", destination_label=f"{destination_date:{date_format}}",
                 month_label=f"{destination_date:%B %Y}", fuel_label=f"{brent_date:%d %b %Y}")
    return inputs, dates


def history_window(prices: pd.DataFrame, years: int, monthly: bool) -> pd.DataFrame:
    """Past prices for the history charts: one row per day, or per month for Dubai.

    Dubai is only published as a monthly average, so its history is shown as
    monthly averages of every price (month against month, not month against day).
    """
    table = P.monthly_averages(prices) if monthly else prices
    return table[table.index >= prices.index.max() - pd.DateOffset(years=years)]


def verdict_banner(result) -> None:
    """The headline: is the arb open or closed, and by how much."""
    line = (f"{usd(result.margin_per_bbl)} per barrel, "
            f"{usd(result.margin_total_usd / 1e6, 1)} million on the cargo")
    if result.is_open:
        st.success(f"### ARB OPEN\nShipping this cargo makes {line}.", icon=":material/check_circle:")
    else:
        st.error(f"### ARB CLOSED\nShipping this cargo loses {line.replace('-', '')}.",
                 icon=":material/cancel:")
