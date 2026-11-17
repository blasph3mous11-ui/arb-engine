"""The arbitrage engine: is it profitable to move this cargo today?

    landed cost  = price paid at origin + every cost of getting it there
    sale value   = benchmark price at destination, adjusted for quality
    margin       = sale value - landed cost

If the margin is positive the "arb is open": the trade pays. If negative it is
closed. Everything is worked per barrel loaded.
"""

from dataclasses import dataclass, replace

from engine import assumptions as A
from engine import costs as C
from engine.units import barrels_to_tonnes
from engine.voyage import VoyageResult, get_vessel, implied_tce, voyage_from_assumptions


@dataclass(frozen=True)
class ArbInputs:
    # The trade
    origin_key: str
    destination_key: str
    vessel_key: str
    via: str                              # "suez", "cape" or "direct"
    cargo_bbl: float
    grade: str                            # the crude being shipped, e.g. "wti"
    destination_benchmark: str            # what it is priced against, e.g. "brent"
    # Prices, USD per barrel
    origin_benchmark_price: float
    destination_benchmark_price: float
    origin_differential: float
    destination_differential: float
    # Freight drivers
    hire_usd_per_day: float
    bunker_usd_per_tonne: float
    charge_ballast_leg: bool
    include_war_risk: bool
    # Other costs
    interest_rate_pct: float              # benchmark rate plus bank margin
    financing_extra_days: float
    insurance_rate_pct: float
    transit_loss_pct: float
    delay_days: float
    # A broker's freight quote for the whole cargo, in USD. None means freight is
    # built from the daily hire rate, fuel, ports and canal instead.
    freight_override_usd: float | None = None

    def with_changes(self, **changes) -> "ArbInputs":
        return replace(self, **changes)


def default_inputs(origin_benchmark_price: float, destination_benchmark_price: float,
                   bunker_usd_per_tonne: float, **overrides) -> ArbInputs:
    """The starting case, with every non-price number taken from the YAML files."""
    vessel_key = overrides.get("vessel_key", "suezmax")
    market = A.get("market", "default_freight_market")
    base = dict(
        origin_key="corpus_christi",
        destination_key="sikka",
        vessel_key=vessel_key,
        via="suez",
        cargo_bbl=get_vessel(vessel_key).cargo_capacity_bbl,
        grade="wti",
        destination_benchmark="brent",
        origin_benchmark_price=origin_benchmark_price,
        destination_benchmark_price=destination_benchmark_price,
        origin_differential=A.get("costs", "pricing", "origin_differential_usd_per_bbl"),
        destination_differential=A.get("costs", "pricing", "destination_differential_usd_per_bbl"),
        hire_usd_per_day=A.get("market", "freight_markets", market, "hire_usd_per_day", vessel_key),
        bunker_usd_per_tonne=bunker_usd_per_tonne,
        charge_ballast_leg=A.get("costs", "voyage_basis", "charge_ballast_leg"),
        include_war_risk=True,
        interest_rate_pct=(A.get("costs", "financing", "benchmark_rate_pct")
                           + A.get("costs", "financing", "margin_pct")),
        financing_extra_days=A.get("costs", "financing", "extra_days"),
        insurance_rate_pct=A.get("costs", "insurance", "cargo_rate_pct"),
        transit_loss_pct=A.get("costs", "transit_loss", "loss_pct"),
        delay_days=A.get("costs", "demurrage", "default_delay_days"),
    )
    base.update(overrides)
    return ArbInputs(**base)


def grade_quality_differential(grade: str, benchmark: str) -> float:
    """Value of the shipped grade relative to the destination benchmark, USD per barrel."""
    grades, rule = A.load("costs")["grades"], A.load("costs")["quality"]
    return C.quality_differential(
        grade_api=A.val(grades[grade]["api_gravity"]),
        grade_sulphur_pct=A.val(grades[grade]["sulphur_pct"]),
        benchmark_api=A.val(grades[benchmark]["api_gravity"]),
        benchmark_sulphur_pct=A.val(grades[benchmark]["sulphur_pct"]),
        usd_per_api_degree=A.val(rule["usd_per_api_degree"]),
        usd_per_sulphur_pct=A.val(rule["usd_per_sulphur_pct"]),
    )


@dataclass
class ArbResult:
    inputs: ArbInputs
    voyage: VoyageResult
    purchase_price: float        # USD/bbl paid at origin (free on board)
    cost_stack: dict             # USD/bbl for each cost between origin and destination
    quality_differential: float  # USD/bbl
    sale_value: float            # USD/bbl received at destination

    @property
    def landed_cost(self) -> float:
        return self.purchase_price + sum(self.cost_stack.values())

    @property
    def margin_per_bbl(self) -> float:
        return self.sale_value - self.landed_cost

    @property
    def margin_total_usd(self) -> float:
        return self.margin_per_bbl * self.inputs.cargo_bbl

    @property
    def is_open(self) -> bool:
        return self.margin_per_bbl > 0

    @property
    def implied_tce(self) -> float:
        """What the shipowner earns per day on this freight (time charter equivalent)."""
        return implied_tce(self.voyage, self.cost_stack["Freight"] * self.inputs.cargo_bbl)

    @property
    def benchmark_spread(self) -> float:
        """Destination benchmark minus origin benchmark, USD/bbl."""
        return self.inputs.destination_benchmark_price - self.inputs.origin_benchmark_price


def run(inputs: ArbInputs) -> ArbResult:
    """Run the whole calculation for one set of inputs."""
    vessel = get_vessel(inputs.vessel_key)
    voyage = voyage_from_assumptions(
        inputs.origin_key, inputs.destination_key, inputs.vessel_key, inputs.via,
        hire_usd_per_day=inputs.hire_usd_per_day,
        bunker_usd_per_tonne=inputs.bunker_usd_per_tonne,
        cargo_bbl=inputs.cargo_bbl,
        charge_ballast_leg=inputs.charge_ballast_leg,
        include_war_risk=inputs.include_war_risk,
    )
    barrels = inputs.cargo_bbl

    # What we pay at the load port, and what the cargo is worth at destination.
    purchase_price = inputs.origin_benchmark_price + inputs.origin_differential
    quality = grade_quality_differential(inputs.grade, inputs.destination_benchmark)
    sale_value = inputs.destination_benchmark_price + inputs.destination_differential + quality

    cargo_value = purchase_price * barrels
    # A broker's quote, when given, replaces the freight built up from the daily hire rate.
    freight = voyage.total_cost if inputs.freight_override_usd is None else inputs.freight_override_usd
    # Demurrage tracks what the ship earns per day: the hire rate, or the quote's implied TCE.
    daily_rate = (inputs.hire_usd_per_day if inputs.freight_override_usd is None
                  else max(implied_tce(voyage, freight), 0.0))

    # Money is tied up from loading until the buyer pays.
    financed_days = voyage.laden_days + inputs.delay_days + inputs.financing_extra_days
    financing = C.financing_cost(cargo_value, inputs.interest_rate_pct, financed_days,
                                 A.get("costs", "financing", "day_count"))
    insurance = C.insurance_cost(cargo_value, freight, inputs.insurance_rate_pct,
                                 A.get("costs", "insurance", "insured_value_uplift_pct"))
    loss = C.transit_loss_cost(sale_value * barrels, inputs.transit_loss_pct)
    demurrage = C.demurrage_cost(inputs.delay_days, daily_rate,
                                 A.get("costs", "demurrage", "rate_as_share_of_hire"),
                                 vessel.idle_consumption_tpd, inputs.bunker_usd_per_tonne)

    cost_stack = {
        "Freight": freight / barrels,
        "Financing": financing / barrels,
        "Insurance": insurance / barrels,
        "Transit loss": loss / barrels,
        "Demurrage": demurrage / barrels,
    }
    return ArbResult(inputs=inputs, voyage=voyage, purchase_price=purchase_price,
                     cost_stack=cost_stack, quality_differential=quality, sale_value=sale_value)


def cargo_tonnes(cargo_bbl: float, grade: str) -> float:
    """The cargo's weight in tonnes, from its volume and the grade's API gravity."""
    return barrels_to_tonnes(cargo_bbl, A.get("costs", "grades", grade, "api_gravity"))
