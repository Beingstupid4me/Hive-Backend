from __future__ import annotations

import numpy as np
import pandas as pd


def annualized_volatility(returns: pd.Series) -> float:
    if returns.empty:
        return 0.0
    return float(returns.std(ddof=0) * np.sqrt(252) * 100.0)


def annualized_return(returns: pd.Series) -> float:
    if returns.empty:
        return 0.0
    growth = float((1.0 + returns).prod())
    years = max(len(returns) / 252.0, 1e-6)
    return float((growth ** (1.0 / years) - 1.0) * 100.0)


def sharpe_ratio(returns: pd.Series) -> float:
    vol = returns.std(ddof=0)
    if vol == 0 or returns.empty:
        return 0.0
    return float(np.sqrt(252) * returns.mean() / vol)


def sortino_ratio(returns: pd.Series) -> float:
    downside = returns[returns < 0]
    denom = downside.std(ddof=0)
    if denom == 0 or returns.empty:
        return 0.0
    return float(np.sqrt(252) * returns.mean() / denom)


def max_drawdown_pct(returns: pd.Series) -> float:
    if returns.empty:
        return 0.0
    curve = (1.0 + returns).cumprod()
    peak = curve.cummax()
    drawdown = curve / peak - 1.0
    return float(drawdown.min() * 100.0)


def max_consecutive_wins(returns: pd.Series) -> int:
    best = 0
    streak = 0
    for value in returns:
        if value > 0:
            streak += 1
            best = max(best, streak)
        else:
            streak = 0
    return best
