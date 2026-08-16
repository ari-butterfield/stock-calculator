import math
import statistics


def _arithmetic_returns(closes):
    return [(closes[i] / closes[i - 1] - 1.0) for i in range(1, len(closes))]


def calculate_weekly_return(closes):
    if len(closes) < 2:
        return None
    arith_returns = _arithmetic_returns(closes)
    if not arith_returns:
        return None
    return float(statistics.mean(arith_returns))


def calculate_weekly_return_std(closes):
    if len(closes) < 2:
        return None
    arith_returns = _arithmetic_returns(closes)
    if len(arith_returns) < 2:
        return None
    return float(statistics.stdev(arith_returns))


def calculate_sharpe_ratio(period_return, period_return_std, annual_risk_free_rate=0.04, periods_per_year=52):
    if period_return is None or period_return_std is None:
        return None
    if period_return_std == 0:
        return None
    period_rf = annual_risk_free_rate / periods_per_year
    return float(((period_return - period_rf) / period_return_std) * math.sqrt(periods_per_year))
