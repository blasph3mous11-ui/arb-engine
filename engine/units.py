"""Unit conversions, all in one place.

Oil is traded in barrels (a volume) but ships are sized in tonnes (a weight),
so the two only meet through the oil's density. Density is quoted as API
gravity: the higher the API number, the lighter the oil.
"""

HOURS_PER_DAY = 24
# One cubic metre is 6.2898 barrels. Water weighs one tonne per cubic metre, so
# oil with specific gravity SG weighs SG tonnes per cubic metre.
BARRELS_PER_CUBIC_METRE = 6.2898


def specific_gravity(api_gravity: float) -> float:
    """Density relative to water, from the standard API gravity formula."""
    return 141.5 / (api_gravity + 131.5)


def barrels_per_tonne(api_gravity: float) -> float:
    """How many barrels of this crude make one tonne."""
    return BARRELS_PER_CUBIC_METRE / specific_gravity(api_gravity)


def barrels_to_tonnes(barrels: float, api_gravity: float) -> float:
    return barrels / barrels_per_tonne(api_gravity)


def tonnes_to_barrels(tonnes: float, api_gravity: float) -> float:
    return tonnes * barrels_per_tonne(api_gravity)


def sailing_days(distance_nm: float, speed_knots: float) -> float:
    """Days at sea. A knot is one nautical mile per hour."""
    return distance_nm / (speed_knots * HOURS_PER_DAY)


def usd_per_tonne_to_usd_per_barrel(usd_per_tonne: float, api_gravity: float) -> float:
    return usd_per_tonne / barrels_per_tonne(api_gravity)
