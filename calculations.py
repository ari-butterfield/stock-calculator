import math
import statistics


def _arithmetic_returns(closes):
    return [(closes[i] / closes[i - 1] - 1.0) for i in range(1, len(closes))]


def calculate_peg(pe, growth):
    if not pe or not growth:
        return None
    return pe / (growth * 100)


def calculate_daily_return(closes):
    if len(closes) < 2:
        return None
    arith_returns = _arithmetic_returns(closes)
    if not arith_returns:
        return None
    return float(statistics.mean(arith_returns))


def calculate_daily_return_std(closes):
    if len(closes) < 2:
        return None
    arith_returns = _arithmetic_returns(closes)
    if len(arith_returns) < 2:
        return None
    return float(statistics.stdev(arith_returns))


def calculate_sharpe_ratio(daily_return, daily_return_std, annual_risk_free_rate=0.04):
    if daily_return is None or daily_return_std is None:
        return None
    if daily_return_std == 0:
        return None
    daily_rf = annual_risk_free_rate / 252
    return float(((daily_return - daily_rf) / daily_return_std) * math.sqrt(252))
