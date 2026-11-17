"""Scenarios: what moves the margin, where it breaks even, and how it looked in the past.

Nothing here forecasts anything. Each function re-runs the same arithmetic
with one input changed.
"""

import pandas as pd

from engine import assumptions as A
from engine.arbitrage import ArbInputs, run
from engine.voyage import get_vessel, route_options


def _cut_label(start: float, cut: float, decimals: int) -> str:
    """Label for a "set lower" case, true to the change actually applied.

    A rate cannot go below zero. If the starting value is smaller than the
    planned cut, the bar only shows a cut down to zero, and the label says so.
    """
    if start >= cut:
        return f"-{cut:.{decimals}f} pts"
    if start > 0:
        return f"-{start:.2f} pts (cannot go below 0%)"
    return "no change (already 0%)"


def _freight_case(inputs: ArbInputs, share: float) -> tuple:
    """Tornado row for the cost of the ship: the daily hire rate, or the broker's quote if one is given."""
    if inputs.freight_override_usd is None:
        return (f"Vessel hire rate (+/- {share:.0%})",
                f"-{share:.0%}", inputs.with_changes(hire_usd_per_day=inputs.hire_usd_per_day * (1 - share)),
                f"+{share:.0%}", inputs.with_changes(hire_usd_per_day=inputs.hire_usd_per_day * (1 + share)))
    quote = inputs.freight_override_usd
    return (f"Freight quote (+/- {share:.0%})",
            f"-{share:.0%}", inputs.with_changes(freight_override_usd=quote * (1 - share)),
            f"+{share:.0%}", inputs.with_changes(freight_override_usd=quote * (1 + share)))


def tornado(inputs: ArbInputs, suez_open: bool = True) -> list[dict]:
    """Flex each driver down and up, one at a time, and record the margin.

    Returns one row per driver, sorted so the biggest mover comes first.
    Set suez_open to False when the canal is taken to be closed: the
    "use Suez instead" row is then left out.
    """
    ranges = {k: A.val(v) for k, v in A.load("costs")["scenario_ranges"].items()}
    base = run(inputs).margin_per_bbl
    hire, bunker = ranges["hire_rate_pct"] / 100, ranges["bunker_price_pct"] / 100
    rate, spread = ranges["interest_rate_points"], ranges["price_spread_usd"]
    loss, delay = ranges["transit_loss_points"], ranges["delay_days"]
    # Interest and transit loss cannot be flexed below zero.
    low_rate = max(inputs.interest_rate_pct - rate, 0)
    low_loss = max(inputs.transit_loss_pct - loss, 0)

    # (name, label for low case, inputs for low case, label for high case, inputs for high case)
    cases = [
        (f"Price spread (+/- ${spread:.0f}/bbl)",
         f"-${spread:.0f}", inputs.with_changes(destination_benchmark_price=inputs.destination_benchmark_price - spread),
         f"+${spread:.0f}", inputs.with_changes(destination_benchmark_price=inputs.destination_benchmark_price + spread)),
        _freight_case(inputs, hire),
        (f"Bunker price (+/- {bunker:.0%})",
         f"-{bunker:.0%}", inputs.with_changes(bunker_usd_per_tonne=inputs.bunker_usd_per_tonne * (1 - bunker)),
         f"+{bunker:.0%}", inputs.with_changes(bunker_usd_per_tonne=inputs.bunker_usd_per_tonne * (1 + bunker))),
        (f"Interest rate (+/- {rate:.0f} pts)",
         _cut_label(inputs.interest_rate_pct, rate, 0),
         inputs.with_changes(interest_rate_pct=low_rate),
         f"+{rate:.0f} pts", inputs.with_changes(interest_rate_pct=inputs.interest_rate_pct + rate)),
        (f"Transit loss (+/- {loss:.1f} pts)",
         _cut_label(inputs.transit_loss_pct, loss, 1),
         inputs.with_changes(transit_loss_pct=low_loss),
         f"+{loss:.1f} pts", inputs.with_changes(transit_loss_pct=inputs.transit_loss_pct + loss)),
        (f"Delay at port (+{delay:.0f} days)",
         "no change", inputs,
         f"+{delay:.0f} days", inputs.with_changes(delay_days=inputs.delay_days + delay)),
    ]
    # Switching route is a yes/no change, shown as a one-sided bar.
    # Only offered where both routes exist: not for a voyage that never goes near
    # Suez (US Gulf to Europe), nor for a ship too deep for the canal.
    options = route_options(inputs.origin_key, inputs.destination_key, inputs.vessel_key)
    other = "cape" if inputs.via == "suez" else "suez"
    if inputs.via != "direct" and other in options and (other == "cape" or suez_open):
        label = "Suez closed: go via Cape" if other == "cape" else "Use Suez instead of Cape"
        cases.append((label, "no change", inputs, "switch route", inputs.with_changes(via=other)))

    rows = []
    for name, low_label, low_inputs, high_label, high_inputs in cases:
        low, high = run(low_inputs).margin_per_bbl, run(high_inputs).margin_per_bbl
        rows.append({"driver": name, "base": base,
                     "low_label": low_label, "low_margin": low,
                     "high_label": high_label, "high_margin": high,
                     "swing": abs(high - low)})
    return sorted(rows, key=lambda r: r["swing"], reverse=True)


def grid_axes() -> tuple[list[float], list[float]]:
    """The hire rates and price spreads the grid covers, evenly spaced, from the YAML settings."""
    r = {k: A.val(v) for k, v in A.load("costs")["scenario_ranges"].items()}
    steps = int(r["grid_steps"])

    def spaced(low, high):
        return [low + (high - low) * i / (steps - 1) for i in range(steps)]

    return (spaced(r["grid_hire_min_usd_per_day"], r["grid_hire_max_usd_per_day"]),
            spaced(r["grid_spread_min_usd"], r["grid_spread_max_usd"]))


def margin_grid(inputs: ArbInputs, hire_values: list[float], spread_values: list[float]) -> pd.DataFrame:
    """Margin per barrel for every pairing of ship hire rate and price spread.

    Rows are price spreads (destination benchmark minus origin benchmark), columns
    are daily hire rates. Everything else is held at the values in `inputs`. The
    spread is changed by moving the destination price, exactly as the break-even
    calculation does, so the two agree.
    """
    grid = pd.DataFrame(index=spread_values, columns=hire_values, dtype=float)
    for spread in spread_values:
        for hire in hire_values:
            changed = inputs.with_changes(
                hire_usd_per_day=hire,
                destination_benchmark_price=inputs.origin_benchmark_price + spread)
            grid.loc[spread, hire] = run(changed).margin_per_bbl
    return grid


def breakeven_spread(inputs: ArbInputs) -> float:
    """The price gap (destination benchmark minus origin benchmark) at which the margin is zero.

    The margin rises in a straight line as the destination price rises, so two
    runs are enough to find where it crosses zero.
    """
    step = 1.0
    m0 = run(inputs).margin_per_bbl
    m1 = run(inputs.with_changes(
        destination_benchmark_price=inputs.destination_benchmark_price + step)).margin_per_bbl
    slope = (m1 - m0) / step
    current_spread = inputs.destination_benchmark_price - inputs.origin_benchmark_price
    return current_spread - m0 / slope


def historical_run(prices: pd.DataFrame, inputs: ArbInputs, origin_column: str,
                   destination_column: str, bunker_ratio: float | None = None) -> pd.DataFrame:
    """Re-run today's model on each row of a table of past prices.

    The table has one row per day, or one row per month when monthly averages
    are passed in (see prices.monthly_averages; needed for Dubai, which is
    only published as a monthly average).

    Only the crude prices (and, if a ratio is given, the bunker price derived
    from Brent) change from row to row. The hire rate, canal tolls, interest rate
    and every other input are held at today's values, which is a big
    simplification: in reality freight moves a lot. Read the result as "what
    would past price gaps have earned at today's costs", not as history.
    """
    rows = []
    usable = prices.dropna(subset=[origin_column, destination_column])
    for date, row in usable.iterrows():
        changes = dict(origin_benchmark_price=float(row[origin_column]),
                       destination_benchmark_price=float(row[destination_column]))
        if bunker_ratio is not None and pd.notna(row.get("brent")):
            changes["bunker_usd_per_tonne"] = float(row["brent"]) * bunker_ratio
        result = run(inputs.with_changes(**changes))
        rows.append({"date": date,
                     "spread": result.benchmark_spread,
                     "freight": result.cost_stack["Freight"],
                     "landed_cost": result.landed_cost,
                     "sale_value": result.sale_value,
                     "margin": result.margin_per_bbl})
    return pd.DataFrame(rows).set_index("date") if rows else pd.DataFrame(
        columns=["spread", "freight", "landed_cost", "sale_value", "margin"])
