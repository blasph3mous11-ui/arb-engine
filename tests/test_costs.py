"""Each cost line, checked against a sum done by hand."""

import pytest

from engine import costs


def test_financing_cost():
    # $90m borrowed at 6% a year for 30 days: 90,000,000 x 0.06 x 30 / 360 = $450,000.
    assert costs.financing_cost(90_000_000, 6.0, 30) == pytest.approx(450_000)


def test_insurance_cost():
    # Cargo $90m + freight $10m = $100m, insured at 110% = $110m, at 0.05% = $55,000.
    assert costs.insurance_cost(90_000_000, 10_000_000, 0.05, 110) == pytest.approx(55_000)


def test_transit_loss_cost():
    # 0.2% of a cargo worth $100m at destination = $200,000.
    assert costs.transit_loss_cost(100_000_000, 0.2) == pytest.approx(200_000)


def test_quality_differential_light_sweet_versus_sour():
    # WTI (39.6 API, 0.24% S) against Dubai (31.0 API, 2.0% S), at $0.40 per degree
    # and $1.00 per point of sulphur:
    #   gravity: (39.6 - 31.0) x 0.40 = +3.44    sulphur: (0.24 - 2.0) x 1.00 = -1.76 penalty
    #   so WTI is worth 3.44 + 1.76 = $5.20 a barrel more.
    assert costs.quality_differential(39.6, 0.24, 31.0, 2.0, 0.40, 1.00) == pytest.approx(5.20)


def test_quality_differential_against_similar_grade():
    # WTI against Brent (38.3 API, 0.37% S): 1.3 x 0.40 = 0.52, plus 0.13 x 1.00 = $0.65.
    assert costs.quality_differential(39.6, 0.24, 38.3, 0.37, 0.40, 1.00) == pytest.approx(0.65)


def test_quality_differential_is_zero_for_the_benchmark_itself():
    assert costs.quality_differential(38.3, 0.37, 38.3, 0.37, 0.40, 1.00) == pytest.approx(0)


def test_demurrage_cost():
    # 3 days late at $50,000 a day, plus idle fuel 7.5 t x $600 = $4,500 a day:
    # 3 x 54,500 = $163,500.
    assert costs.demurrage_cost(3, 50_000, 1.0, 7.5, 600) == pytest.approx(163_500)


def test_no_delay_means_no_demurrage():
    assert costs.demurrage_cost(0, 50_000, 1.0, 7.5, 600) == 0
