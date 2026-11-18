"""A recap of one trade, line by line, for download as a spreadsheet.

Traders send each other a short recap of a deal: what, where, on what ship, at
what prices, and what it leaves. This builds that list from one calculation, and
says against every line whether it is a published figure, an estimate, a figure
the user typed in, or arithmetic on the lines above.
"""

from engine import assumptions as A
from engine.arbitrage import ArbResult
from engine.voyage import ROUTES, get_port, get_vessel

PUBLISHED, ESTIMATED, CALCULATED, TYPED = "published", "estimated", "calculated", "typed in"
DISCLAIMER = ("Model output built from public benchmark prices and documented estimates; it does not use "
              "traded freight rates or physical premium data. Sources for every assumption are on the "
              "dashboard's Methodology page.")


def trade_recap(result: ArbResult, context: dict) -> list[dict]:
    """One row per line: section, item, value, unit, basis.

    context holds what the calculation does not know: "origin_price_label" and
    "destination_price_label" (benchmark name and date), "freight_label" (how freight
    was set), "hire_is_estimate" and "made_on" (the date of the recap).
    """
    inputs, voyage = result.inputs, result.voyage
    grade = A.val(A.load("costs")["grades"][inputs.grade]["name"])
    rows = []

    def add(section, item, value, unit, basis):
        rows.append({"Section": section, "Item": item,
                     "Value": round(value, 4) if isinstance(value, float) else value,
                     "Unit": unit, "Basis": basis})

    add("Trade", "Load port", get_port(inputs.origin_key)["name"], "", "")
    add("Trade", "Discharge port", get_port(inputs.destination_key)["name"], "", "")
    add("Trade", "Ship", get_vessel(inputs.vessel_key).name, "", "")
    add("Trade", "Cargo", float(inputs.cargo_bbl), "barrels", ESTIMATED)
    add("Trade", "Crude grade", grade, "", "")
    add("Trade", "Route", ROUTES[inputs.via], "", "")
    add("Trade", "Freight set by", context["freight_label"], "", "")
    add("Voyage", "Speed loaded", float(voyage.speeds["laden"]), "knots",
        TYPED if inputs.speed_mode == "custom" else ESTIMATED)
    add("Voyage", "Speed empty", float(voyage.speeds["ballast"]), "knots",
        TYPED if inputs.speed_mode == "custom" else ESTIMATED)
    add("Voyage", "Distance, one way", float(voyage.distance_nm), "nautical miles",
        "calculated (searoute sea-lane model)")
    add("Voyage", "Days loaded", float(voyage.laden_days), "days", CALCULATED)
    add("Voyage", "Days the ship is tied up", float(voyage.total_days), "days", CALCULATED)
    add("Voyage", "Fuel burned", float(voyage.total_fuel_tonnes), "tonnes", ESTIMATED)

    add("Prices", context["origin_price_label"], float(inputs.origin_benchmark_price), "USD per barrel", PUBLISHED)
    add("Prices", "Grade differential at the load port", float(inputs.origin_differential),
        "USD per barrel", ESTIMATED)
    add("Prices", "Purchase price", float(result.purchase_price), "USD per barrel", CALCULATED)
    add("Prices", context["destination_price_label"], float(inputs.destination_benchmark_price),
        "USD per barrel", PUBLISHED)
    add("Prices", "Quality adjustment", float(result.quality_differential), "USD per barrel", ESTIMATED)
    add("Prices", "Destination differential", float(inputs.destination_differential), "USD per barrel", ESTIMATED)
    add("Prices", "Futures curve effect (hedged)", float(result.curve_value), "USD per barrel",
        TYPED if inputs.curve_m2_minus_m1 else ESTIMATED)
    add("Prices", "Sale value", float(result.sale_value), "USD per barrel", CALCULATED)

    if inputs.freight_override_usd is None:
        for name, cost in voyage.per_bbl().items():
            add("Freight breakdown", name, float(cost), "USD per barrel", ESTIMATED)
    else:
        add("Freight breakdown", "Broker's quote for the cargo", float(inputs.freight_override_usd), "USD", TYPED)
        add("Freight breakdown", "Owner's daily earnings implied (TCE)", float(result.implied_tce),
            "USD per day", ESTIMATED)
    for name, cost in result.cost_stack.items():
        add("Costs", name, float(cost), "USD per barrel", ESTIMATED)

    add("Result", "Landed cost", float(result.landed_cost), "USD per barrel", CALCULATED)
    add("Result", "Margin", float(result.margin_per_bbl), "USD per barrel", CALCULATED)
    add("Result", "Margin on the cargo", float(result.margin_total_usd), "USD", CALCULATED)
    add("Result", "Verdict", "ARB OPEN" if result.is_open else "ARB CLOSED", "", CALCULATED)

    add("Inputs", "Ship hire", float(inputs.hire_usd_per_day), "USD per day",
        ESTIMATED if context["hire_is_estimate"] else PUBLISHED)
    add("Inputs", "Fuel (bunker) price", float(inputs.bunker_usd_per_tonne), "USD per tonne", ESTIMATED)
    add("Inputs", "Interest rate (SOFR plus bank margin)", float(inputs.interest_rate_pct),
        "percent a year", "SOFR published, bank margin estimated")
    add("Inputs", "Cargo insurance", float(inputs.insurance_rate_pct), "percent", ESTIMATED)
    add("Inputs", "Transit loss", float(inputs.transit_loss_pct), "percent", ESTIMATED)
    add("Inputs", "Delay days", float(inputs.delay_days), "days", ESTIMATED)

    add("Note", "Made on", context["made_on"], "", "")
    add("Note", "What this is", DISCLAIMER, "", "")
    return rows
