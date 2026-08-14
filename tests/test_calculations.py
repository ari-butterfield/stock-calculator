import math
import statistics

import pytest

from calculations import (
    calculate_peg,
    calculate_daily_return,
    calculate_daily_return_std,
    calculate_sharpe_ratio,
)


def test_calculate_peg_basic():
    assert calculate_peg(20, 0.10) == pytest.approx(2.0)


def test_calculate_peg_negative_growth_is_not_treated_as_missing():
    # Matches real-world behavior seen in the live app (e.g. a high-growth,
    # currently-unprofitable stock can have negative earningsGrowth).
    assert calculate_peg(20, -0.05) == pytest.approx(-4.0)


def test_calculate_peg_missing_inputs_returns_none():
    assert calculate_peg(None, 0.10) is None
    assert calculate_peg(20, None) is None
    assert calculate_peg(20, 0) is None


def test_calculate_daily_return_single_period_exact():
    # Hand-computed, independent of the implementation: one 10% up day.
    assert calculate_daily_return([100.0, 110.0]) == pytest.approx(0.10)


CLOSES = [100.0, 110.0, 100.0, 95.0, 105.0]


def test_calculate_daily_return_matches_manual_mean():
    expected = statistics.mean(
        [(CLOSES[i] / CLOSES[i - 1] - 1.0) for i in range(1, len(CLOSES))]
    )
    assert calculate_daily_return(CLOSES) == pytest.approx(expected)


def test_calculate_daily_return_std_matches_manual_stdev():
    expected = statistics.stdev(
        [(CLOSES[i] / CLOSES[i - 1] - 1.0) for i in range(1, len(CLOSES))]
    )
    assert calculate_daily_return_std(CLOSES) == pytest.approx(expected)


def test_calculate_daily_return_std_returns_none_for_single_period():
    assert calculate_daily_return_std([100.0, 105.0]) is None


def test_calculate_sharpe_ratio_zero_when_return_equals_risk_free():
    annual_rf = 0.04
    daily_rf = annual_rf / 252
    assert calculate_sharpe_ratio(daily_rf, 0.01, annual_rf) == pytest.approx(0.0, abs=1e-9)


def test_calculate_sharpe_ratio_matches_manual_computation():
    dr = calculate_daily_return(CLOSES)
    dstd = calculate_daily_return_std(CLOSES)
    annual_rf = 0.04
    daily_rf = annual_rf / 252
    expected = ((dr - daily_rf) / dstd) * math.sqrt(252)
    assert calculate_sharpe_ratio(dr, dstd, annual_rf) == pytest.approx(expected)


def test_calculate_sharpe_ratio_none_inputs_return_none():
    assert calculate_sharpe_ratio(None, 0.01) is None
    assert calculate_sharpe_ratio(0.001, None) is None


def test_calculate_sharpe_ratio_zero_std_returns_none():
    assert calculate_sharpe_ratio(0.001, 0.0) is None
