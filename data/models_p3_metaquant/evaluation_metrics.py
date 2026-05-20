"""
Institutional-Grade Evaluation Metrics
Senior Quant Standards (AQR/Two Sigma caliber)

Includes:
  - Jensen's Alpha: risk-adjusted excess return relative to CAPM
  - Beta: systematic risk measurement (market sensitivity)
  - Information Ratio: alpha per unit of tracking error
  - Sharpe, Sortino, Calmar, Profit Factor
  - Statistical significance via deflated Sharpe and bootstrap
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple, Optional
from scipy import stats
import warnings

warnings.filterwarnings('ignore')


class PerformanceMetrics:
    """Comprehensive portfolio evaluation framework."""

    def __init__(
        self,
        returns: pd.Series,
        benchmark_returns: Optional[pd.Series] = None,
        risk_free_rate: float = 0.02,
        periods_per_year: int = 252
    ):
        """
        Initialize metrics calculator.

        Args:
            returns: Portfolio daily log returns (Series, index=date)
            benchmark_returns: Optional benchmark returns (e.g., S&P 500)
            risk_free_rate: Annual risk-free rate (default 2%)
            periods_per_year: Trading periods per year (default 252)
        """
        self.returns = returns.dropna()
        self.benchmark_returns = benchmark_returns
        self.rf = risk_free_rate / periods_per_year
        self.periods_per_year = periods_per_year
        
    # ──────────────────────────────────────────────────────────────────────────
    # CAPM & RISK METRICS
    # ──────────────────────────────────────────────────────────────────────────
    
    def beta(self) -> float:
        """
        Calculate portfolio beta (systematic risk).
        
        Beta = Cov(Portfolio, Benchmark) / Var(Benchmark)
        
        Interpretation:
          β=1.0 : moves with market
          β>1.0 : amplifies market moves (more volatile)
          β<1.0 : dampens market moves (more stable)
          β=0   : market-neutral
        """
        if self.benchmark_returns is None:
            return np.nan
        
        # Align dates
        joined = pd.DataFrame({
            'port': self.returns,
            'bench': self.benchmark_returns
        }).dropna()
        
        if len(joined) < 30:
            return np.nan
        
        port_ret = joined['port'].values
        bench_ret = joined['bench'].values
        
        covariance = np.cov(port_ret, bench_ret)[0, 1]
        market_var = np.var(bench_ret, ddof=1)
        
        return covariance / market_var if market_var > 0 else np.nan
    
    def jensen_alpha(self) -> float:
        """
        Calculate Jensen's Alpha (risk-adjusted excess return).
        
        α = r_p - [r_f + β(r_m - r_f)]
        
        Where:
          r_p = portfolio return
          r_f = risk-free rate
          β   = portfolio beta
          r_m = benchmark return
        
        Interpretation:
          α>0  : outperformance (positive alpha)
          α<0  : underperformance (negative alpha)
          
        Units: annualized percentage
        """
        if self.benchmark_returns is None:
            return np.nan
        
        # Align dates
        joined = pd.DataFrame({
            'port': self.returns,
            'bench': self.benchmark_returns
        }).dropna()
        
        if len(joined) < 30:
            return np.nan
        
        # Annualized returns
        port_ret_annual = joined['port'].mean() * self.periods_per_year
        bench_ret_annual = joined['bench'].mean() * self.periods_per_year
        
        # Beta
        beta = self.beta()
        if np.isnan(beta):
            return np.nan
        
        # Jensen's Alpha = portfolio return - CAPM return
        capm_return = self.rf * self.periods_per_year + beta * (bench_ret_annual - self.rf * self.periods_per_year)
        alpha = port_ret_annual - capm_return
        
        return alpha
    
    # ──────────────────────────────────────────────────────────────────────────
    # INFORMATION RATIO & TRACKING ERROR
    # ──────────────────────────────────────────────────────────────────────────
    
    def tracking_error(self) -> float:
        """
        Calculate tracking error (relative volatility to benchmark).
        
        TE = std(portfolio_return - benchmark_return)
        
        Interpretation:
          TE = 0   : perfect replication
          TE < 1%  : tight active management
          TE > 5%  : significant deviations allowed
          
        Units: annualized percentage
        """
        if self.benchmark_returns is None:
            return np.nan
        
        # Align dates
        joined = pd.DataFrame({
            'port': self.returns,
            'bench': self.benchmark_returns
        }).dropna()
        
        if len(joined) < 30:
            return np.nan
        
        tracking_err_daily = joined['port'] - joined['bench']
        te = tracking_err_daily.std() * np.sqrt(self.periods_per_year)
        
        return te
    
    def information_ratio(self) -> float:
        """
        Calculate Information Ratio (alpha per unit of active risk).
        
        IR = (r_p - r_b) / TE
        
        Where:
          r_p = portfolio return
          r_b = benchmark return
          TE  = tracking error
        
        Interpretation:
          IR > 1.0  : excellent active management
          IR > 0.5  : good active management
          IR < 0    : underperformance vs benchmark
          
        Units: ratio (dimensionless)
        """
        if self.benchmark_returns is None:
            return np.nan
        
        # Align dates
        joined = pd.DataFrame({
            'port': self.returns,
            'bench': self.benchmark_returns
        }).dropna()
        
        if len(joined) < 30:
            return np.nan
        
        # Excess returns (annualized)
        port_ret_annual = joined['port'].mean() * self.periods_per_year
        bench_ret_annual = joined['bench'].mean() * self.periods_per_year
        excess_return = port_ret_annual - bench_ret_annual
        
        # Tracking error
        te = self.tracking_error()
        if te is None or te == 0:
            return np.nan
        
        ir = excess_return / te
        return ir
    
    # ──────────────────────────────────────────────────────────────────────────
    # CORE PERFORMANCE METRICS
    # ──────────────────────────────────────────────────────────────────────────
    
    def annual_return(self) -> float:
        """Annualized return (geometric mean)."""
        if len(self.returns) == 0:
            return np.nan
        cum_ret = (1 + self.returns).prod()
        years = len(self.returns) / self.periods_per_year
        return (cum_ret ** (1 / years)) - 1 if years > 0 else np.nan
    
    def annual_volatility(self) -> float:
        """Annualized volatility (standard deviation)."""
        if len(self.returns) < 2:
            return np.nan
        return self.returns.std() * np.sqrt(self.periods_per_year)
    
    def sharpe_ratio(self) -> float:
        """
        Sharpe Ratio = (return - rf) / volatility
        
        Risk-adjusted return per unit of total volatility.
        """
        vol = self.annual_volatility()
        if vol == 0 or np.isnan(vol):
            return 0.0
        
        ret = self.annual_return()
        if np.isnan(ret):
            return 0.0
        
        return (ret - self.rf * self.periods_per_year) / vol
    
    def sortino_ratio(self) -> float:
        """
        Sortino Ratio = (return - rf) / downside_deviation
        
        Only penalizes downside volatility (negative returns).
        """
        downside_rets = self.returns[self.returns < 0]
        if len(downside_rets) == 0:
            return np.inf
        
        downside_dev = downside_rets.std() * np.sqrt(self.periods_per_year)
        if downside_dev == 0:
            return np.inf
        
        ret = self.annual_return()
        if np.isnan(ret):
            return 0.0
        
        return (ret - self.rf * self.periods_per_year) / downside_dev
    
    def max_drawdown(self) -> float:
        """Maximum peak-to-trough decline."""
        cum_ret = (1 + self.returns).cumprod()
        running_max = cum_ret.expanding().max()
        drawdown = (cum_ret - running_max) / running_max
        return drawdown.min()
    
    def calmar_ratio(self) -> float:
        """Calmar = annual_return / abs(max_drawdown)."""
        mdd = self.max_drawdown()
        if mdd == 0 or mdd > 0:  # no drawdown or positive (shouldn't happen)
            return np.inf
        
        ret = self.annual_return()
        if np.isnan(ret):
            return 0.0
        
        return ret / (-mdd)
    
    def profit_factor(self) -> float:
        """Ratio of sum of gains to sum of losses."""
        gains = self.returns[self.returns > 0].sum()
        losses = abs(self.returns[self.returns < 0].sum())
        
        if losses == 0:
            return np.inf if gains > 0 else 0.0
        
        return gains / losses
    
    def win_rate(self) -> float:
        """Percentage of positive return days."""
        if len(self.returns) == 0:
            return 0.0
        return (self.returns > 0).mean()
    
    def value_at_risk(self, confidence: float = 0.95) -> float:
        """Value at Risk at given confidence level (e.g., 95%)."""
        return np.percentile(self.returns, (1 - confidence) * 100)
    
    def conditional_value_at_risk(self, confidence: float = 0.95) -> float:
        """CVaR = expected loss given we exceed VaR threshold."""
        var = self.value_at_risk(confidence)
        return self.returns[self.returns <= var].mean()
    
    # ──────────────────────────────────────────────────────────────────────────
    # STATISTICAL SIGNIFICANCE
    # ──────────────────────────────────────────────────────────────────────────
    
    def deflated_sharpe_ratio(
        self,
        n_trials: int = 100,
        correlation: float = 0.5
    ) -> float:
        """
        Deflated Sharpe Ratio accounts for multiple testing bias.
        
        DSR ≈ Sharpe * sqrt(1 - (π/2)^0.5 * ν / n * correlation)
        
        Where:
          ν = degrees of freedom (typically n_trials)
          n = number of observations
          
        Interpretation:
          DSR > 0 @ p=0.05 : statistically significant result
          DSR < 0         : likely overfitting/backtest bias
        """
        sharpe = self.sharpe_ratio()
        n = len(self.returns)
        
        # Multiple testing penalty
        denom = 1 - (np.pi / 2) ** 0.5 * n_trials / n * correlation
        
        if denom <= 0:
            return sharpe  # no deflation if denominator invalid
        
        dsr = sharpe * np.sqrt(denom)
        return dsr
    
    def sharpe_pvalue(self) -> float:
        """
        Estimate p-value of Sharpe Ratio via t-test.
        
        H0: Sharpe = 0 (no excess return)
        HA: Sharpe ≠ 0
        """
        sharpe = self.sharpe_ratio()
        n = len(self.returns)
        
        # t-stat = sharpe * sqrt(n)
        t_stat = sharpe * np.sqrt(n)
        
        # 2-tailed t-test
        p_val = 2 * (1 - stats.t.cdf(abs(t_stat), df=n-1))
        return p_val
    
    def bootstrap_ci(
        self,
        metric_fn,
        n_bootstrap: int = 1000,
        ci: float = 0.95,
        seed: int = 42
    ) -> Tuple[float, float]:
        """
        Bootstrap confidence interval for a metric.
        
        Args:
            metric_fn: Function that takes returns and returns a scalar
            n_bootstrap: Number of bootstrap samples
            ci: Confidence level (e.g., 0.95)
            seed: Random seed
        
        Returns:
            (lower_ci, upper_ci)
        """
        np.random.seed(seed)
        bootstrap_stats = []
        
        for _ in range(n_bootstrap):
            # Resample with replacement
            idx = np.random.choice(len(self.returns), size=len(self.returns), replace=True)
            resampled = self.returns.iloc[idx]
            
            # Compute metric
            try:
                stat = metric_fn(resampled)
                if not np.isnan(stat):
                    bootstrap_stats.append(stat)
            except:
                pass
        
        if len(bootstrap_stats) == 0:
            return (np.nan, np.nan)
        
        bootstrap_stats = np.array(bootstrap_stats)
        alpha = 1 - ci
        lower = np.percentile(bootstrap_stats, (alpha/2) * 100)
        upper = np.percentile(bootstrap_stats, (1 - alpha/2) * 100)
        
        return (lower, upper)
    
    # ──────────────────────────────────────────────────────────────────────────
    # REPORTING
    # ──────────────────────────────────────────────────────────────────────────
    
    def full_report(self) -> Dict:
        """Generate comprehensive performance report."""
        report = {
            # Core Returns
            'Annual Return': f"{self.annual_return() * 100:.2f}%",
            'Total Return': f"{((1 + self.returns).prod() - 1) * 100:.2f}%",
            
            # Risk Metrics
            'Annual Volatility': f"{self.annual_volatility() * 100:.2f}%",
            'Max Drawdown': f"{self.max_drawdown() * 100:.2f}%",
            
            # Risk-Adjusted Returns
            'Sharpe Ratio': f"{self.sharpe_ratio():.3f}",
            'Sortino Ratio': f"{self.sortino_ratio():.3f}",
            'Calmar Ratio': f"{self.calmar_ratio():.3f}",
            
            # Win/Loss Stats
            'Win Rate': f"{self.win_rate() * 100:.1f}%",
            'Profit Factor': f"{self.profit_factor():.3f}",
            
            # Downside Metrics
            'VaR (95%)': f"{self.value_at_risk() * 100:.3f}%",
            'CVaR (95%)': f"{self.conditional_value_at_risk() * 100:.3f}%",
            
            # CAPM (if benchmark available)
            'Beta': f"{self.beta():.3f}" if not np.isnan(self.beta()) else "N/A",
            "Jensen's Alpha": f"{self.jensen_alpha() * 100:.3f}%" if not np.isnan(self.jensen_alpha()) else "N/A",
            'Information Ratio': f"{self.information_ratio():.3f}" if not np.isnan(self.information_ratio()) else "N/A",
            'Tracking Error': f"{self.tracking_error() * 100:.3f}%" if not np.isnan(self.tracking_error()) else "N/A",
            
            # Statistical Significance
            'Deflated Sharpe': f"{self.deflated_sharpe_ratio():.3f}",
            'Sharpe p-value': f"{self.sharpe_pvalue():.4f}",
            'Observations': len(self.returns),
        }
        return report
    
    def to_dataframe(self) -> pd.DataFrame:
        """Convert report to DataFrame for export."""
        report = self.full_report()
        return pd.DataFrame([report]).T.rename(columns={0: 'Value'})


def compare_strategies(
    strategies: Dict[str, pd.Series],
    benchmark: Optional[pd.Series] = None,
    risk_free_rate: float = 0.02
) -> pd.DataFrame:
    """
    Compare multiple strategies side-by-side.
    
    Args:
        strategies: Dict[strategy_name, returns_series]
        benchmark: Optional benchmark returns
        risk_free_rate: Annual risk-free rate
    
    Returns:
        DataFrame with metrics as rows, strategies as columns
    """
    results = {}
    
    for strat_name, returns in strategies.items():
        metrics = PerformanceMetrics(
            returns,
            benchmark_returns=benchmark,
            risk_free_rate=risk_free_rate
        )
        results[strat_name] = metrics.full_report()
    
    df = pd.DataFrame(results)
    return df


if __name__ == '__main__':
    # Example usage
    print("✓ Evaluation metrics module loaded")
