"""The costs between buying a cargo and selling it, other than freight.

Each function is one line of trading arithmetic, kept separate so it can be
explained and tested on its own.
"""


def financing_cost(cargo_value_usd: float, annual_rate_pct: float, days: float,
                   day_count: int = 360) -> float:
    """Interest on the money tied up in the cargo while it is at sea.

    The trader borrows the cargo value from a bank and repays when the buyer
    pays. Simple interest: value x rate x days / 360.
    """
    return cargo_value_usd * (annual_rate_pct / 100) * days / day_count


def insurance_cost(cargo_value_usd: float, freight_usd: float, rate_pct: float,
                   uplift_pct: float = 110) -> float:
    """Cargo insurance premium.

    Cargo is normally insured for its value plus freight, plus 10%, so that a
    total loss also covers the costs sunk into moving it.
    """
    insured_value = (cargo_value_usd + freight_usd) * uplift_pct / 100
    return insured_value * rate_pct / 100


def transit_loss_cost(sale_value_usd: float, loss_pct: float) -> float:
    """Value of the oil that is loaded but never sold.

    A little less oil is measured out at discharge than was measured in at
    loading. The trader paid for those barrels and shipped them, but cannot
    sell them, so the cost is the sale value of the lost volume.
    """
    return sale_value_usd * loss_pct / 100


def quality_differential(grade_api: float, grade_sulphur_pct: float,
                         benchmark_api: float, benchmark_sulphur_pct: float,
                         usd_per_api_degree: float, usd_per_sulphur_pct: float) -> float:
    """How much more (+) or less (-) a barrel of this grade is worth than the benchmark.

    Lighter oil (higher API) is worth more; more sulphur is worth less. This is
    a straight-line rule of thumb, not a refinery model.
    """
    gravity_value = (grade_api - benchmark_api) * usd_per_api_degree
    sulphur_penalty = (grade_sulphur_pct - benchmark_sulphur_pct) * usd_per_sulphur_pct
    return gravity_value - sulphur_penalty


def demurrage_cost(delay_days: float, hire_usd_per_day: float, rate_as_share_of_hire: float,
                   idle_consumption_tpd: float, bunker_usd_per_tonne: float) -> float:
    """Cost of the ship being held up beyond the agreed time.

    The charterer pays the owner a daily penalty (demurrage), which we set as a
    share of the daily hire rate, plus the fuel the ship burns while it waits.
    """
    daily_rate = hire_usd_per_day * rate_as_share_of_hire
    idle_fuel = idle_consumption_tpd * bunker_usd_per_tonne
    return delay_days * (daily_rate + idle_fuel)
