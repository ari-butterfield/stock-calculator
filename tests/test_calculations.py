import math
import statistics

import pytest

from calculations import (
    calculate_weekly_return,
    calculate_weekly_return_std,
    calculate_sharpe_ratio,
)


def test_calculate_weekly_return_single_period_exact():
    # Hand-computed, independent of the implementation: one 10% up week.
    assert calculate_weekly_return([100.0, 110.0]) == pytest.approx(0.10)


CLOSES = [100.0, 110.0, 100.0, 95.0, 105.0]


def test_calculate_weekly_return_matches_manual_mean():
    expected = statistics.mean(
        [(CLOSES[i] / CLOSES[i - 1] - 1.0) for i in range(1, len(CLOSES))]
    )
    assert calculate_weekly_return(CLOSES) == pytest.approx(expected)


def test_calculate_weekly_return_std_matches_manual_stdev():
    expected = statistics.stdev(
        [(CLOSES[i] / CLOSES[i - 1] - 1.0) for i in range(1, len(CLOSES))]
    )
    assert calculate_weekly_return_std(CLOSES) == pytest.approx(expected)


def test_calculate_weekly_return_std_returns_none_for_single_period():
    assert calculate_weekly_return_std([100.0, 105.0]) is None


def test_calculate_sharpe_ratio_zero_when_return_equals_risk_free():
    annual_rf = 0.04
    weekly_rf = annual_rf / 52
    assert calculate_sharpe_ratio(weekly_rf, 0.01, annual_rf) == pytest.approx(0.0, abs=1e-9)


def test_calculate_sharpe_ratio_matches_manual_computation():
    wr = calculate_weekly_return(CLOSES)
    wstd = calculate_weekly_return_std(CLOSES)
    annual_rf = 0.04
    weekly_rf = annual_rf / 52
    expected = ((wr - weekly_rf) / wstd) * math.sqrt(52)
    assert calculate_sharpe_ratio(wr, wstd, annual_rf) == pytest.approx(expected)


def test_calculate_sharpe_ratio_respects_custom_periods_per_year():
    annual_rf = 0.04
    daily_rf = annual_rf / 252
    expected = ((0.001 - daily_rf) / 0.02) * math.sqrt(252)
    assert calculate_sharpe_ratio(0.001, 0.02, annual_rf, periods_per_year=252) == pytest.approx(expected)


def test_calculate_sharpe_ratio_none_inputs_return_none():
    assert calculate_sharpe_ratio(None, 0.01) is None
    assert calculate_sharpe_ratio(0.001, None) is None


def test_calculate_sharpe_ratio_zero_std_returns_none():
    assert calculate_sharpe_ratio(0.001, 0.0) is None
