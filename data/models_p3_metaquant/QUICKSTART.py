"""
QUICK START GUIDE
================================================================================
Institutional Quant Enhancements - TL;DR

Three new production-grade modules have been added to your pipeline.
This guide gets you running in 5 minutes.
================================================================================
"""

# STEP 1: Run the HRP Glasso Notebook
# ─────────────────────────────────────────────────────────────────────────────
# 
# This generates all portfolio results with Graphical Lasso covariance
#
# In terminal:
#   cd BTP/models_p3_metaquant
#   jupyter notebook 05_hrp_glasso_portfolio.ipynb
#
# Or in Python:
#   import subprocess
#   subprocess.run([
#       'jupyter', 'notebook',
#       '05_hrp_glasso_portfolio.ipynb'
#   ])
#
# Outputs generated:
#   ✓ hrp_glasso_equity_curves.parquet
#   ✓ hrp_glasso_performance_metrics.csv
#   ✓ hrp_glasso_dsr_report.json
#   ✓ hrp_glasso_dashboard.png

# STEP 2: Run the Integration Example
# ─────────────────────────────────────────────────────────────────────────────
#
# This computes all institutional metrics and exports reports
#
# In terminal:
#   python integration_example.py
#
# Or in Python:
import sys
sys.path.insert(0, 'BTP/models_p3_metaquant')
exec(open('BTP/models_p3_metaquant/integration_example.py').read())
#
# Outputs generated in reports/:
#   ✓ Equity curves (Parquet, CSV, Excel, PNG)
#   ✓ DSR metrics (JSON, CSV, PNG)
#   ✓ Comparison dashboard (Excel, PNG)
#   ✓ Executive summary (TXT)
#   ✓ Export manifest (JSON)

# STEP 3: Analyze Results
# ─────────────────────────────────────────────────────────────────────────────

import pandas as pd
from pathlib import Path

# Read performance metrics
metrics = pd.read_csv('BTP/models_p3_metaquant/hrp_glasso_performance_metrics.csv', index_col=0)

print(metrics)
#
# Key columns to check:
#   - Sharpe             → Risk-adjusted return (target > 1.0)
#   - Deflated Sharpe    → Adjusted for overfitting (should be < Sharpe)
#   - Annual Return      → Total return % (target > 10%)
#   - Max Drawdown       → Worst peak-to-trough (target < 20%)
#   - Jensen's Alpha     → Excess return vs. CAPM (target > 0%)
#   - Information Ratio  → Alpha per unit of active risk (target > 0.5)
#   - Beta               → Market sensitivity (0.5-1.0 typical)

# STEP 4: Key Metrics Explained
# ─────────────────────────────────────────────────────────────────────────────

# Jensen's Alpha: Did you beat what your systematic risk (beta) predicts?
#   α > 0%   → Outperformance (good!)
#   α = 0%   → Fairly priced
#   α < 0%   → Underperformance
#   Interpretation: Shows true skill after accounting for market exposure

# Beta: How much do you move with the market?
#   β = 1.0  → Move exactly with market
#   β > 1.0  → More volatile (amplify market moves)
#   β < 1.0  → Less volatile (dampens market moves)
#   Interpretation: Risk measurement for CAPM

# Information Ratio: Active alpha per unit of active risk
#   IR > 1.0 → Excellent active management
#   IR > 0.5 → Good active management
#   IR < 0   → Underperformance
#   Interpretation: Reward for deviating from benchmark

# Deflated Sharpe Ratio: Did we overfit our backtest?
#   DSR ≈ Sharpe → Robust result
#   DSR << Sharpe → Possible overfitting
#   DSR < 0 → Likely spurious alpha
#   Interpretation: Corrects for multiple testing bias

# STEP 5: What's Different in HRP Glasso?
# ─────────────────────────────────────────────────────────────────────────────

# Standard HRP uses empirical covariance (noisy, unstable with many assets)
# HRP+Glasso uses Graphical Lasso (sparse, robust, shrinks spurious correlations)

# Benefits:
#   ✓ Better out-of-sample performance
#   ✓ More stable portfolio weights
#   ✓ Fewer false correlations
#   ✓ Better in high-volatility regimes

# You'll see:
#   - Slightly different weights (especially for small positions)
#   - Potentially lower turnover (more stable positions)
#   - Potentially better Sharpe ratio (fewer spurious bets)

# STEP 6: Using the Metrics Module Directly
# ─────────────────────────────────────────────────────────────────────────────

from evaluation_metrics import PerformanceMetrics

# Your portfolio returns and benchmark returns (daily log returns)
portfolio_rets = pd.read_parquet('BTP/models_p3_metaquant/hrp_glasso_equity_curves.parquet')['HRP_Glasso'].pct_change()
benchmark_rets = pd.read_parquet('BTP/models_p3_metaquant/hrp_glasso_equity_curves.parquet')['Equal_Weight'].pct_change()

# Create metrics calculator
metrics = PerformanceMetrics(
    returns=portfolio_rets,
    benchmark_returns=benchmark_rets,
    risk_free_rate=0.02  # 2% annual
)

# Access individual metrics
print(f"Annual Return:       {metrics.annual_return() * 100:.2f}%")
print(f"Sharpe Ratio:        {metrics.sharpe_ratio():.3f}")
print(f"Beta:                {metrics.beta():.3f}")
print(f"Jensen's Alpha:      {metrics.jensen_alpha() * 100:.3f}%")
print(f"Information Ratio:   {metrics.information_ratio():.3f}")
print(f"Deflated Sharpe:     {metrics.deflated_sharpe_ratio():.3f}")
print(f"Max Drawdown:        {metrics.max_drawdown() * 100:.2f}%")
print(f"Profit Factor:       {metrics.profit_factor():.3f}")

# Full report as dictionary
full_report = metrics.full_report()
for metric, value in full_report.items():
    print(f"{metric}: {value}")

# STEP 7: Using the Report Exporter Directly
# ─────────────────────────────────────────────────────────────────────────────

from report_exporter import ReportExporter
from pathlib import Path

exporter = ReportExporter(output_dir=Path('reports'))

# Export equity curves in all formats
paths = exporter.save_equity_curves(
    strategies={
        'HRP+Glasso': portfolio_rets,
        'Benchmark': benchmark_rets
    },
    tag='my_portfolio'
)
# Returns: {'parquet': Path(...), 'csv': Path(...), 'png': Path(...), 'excel': Path(...)}

# Export DSR metrics
metrics_dict = {
    'Sharpe Ratio': '1.25',
    'Deflated Sharpe': '0.95',
    'Jensen Alpha': '3.2%',
    'Information Ratio': '1.15',
    'Beta': '0.85',
    'Annual Return': '12.5%'
}
dsr_paths = exporter.save_dsr_metrics(metrics_dict, strategy_name='my_portfolio')

# STEP 8: Common Questions
# ─────────────────────────────────────────────────────────────────────────────

# Q: Is my alpha statistically significant?
# A: Check Sharpe p-value < 0.05
#    If Deflated Sharpe ≈ raw Sharpe, likely robust
#    If Deflated Sharpe << raw Sharpe, possible overfitting

# Q: How much market risk am I taking?
# A: Check Beta. β > 0.7 means you're quite exposed to market moves.

# Q: How much is skill vs. luck?
# A: Jensen's Alpha (risk-adjusted) vs. raw return tells the story.
#    Alpha = 0% → it's all luck (just following market)
#    Alpha > 2% → likely skill (after accounting for beta)

# Q: Am I doing better than a simple benchmark?
# A: Check Information Ratio.
#    IR > 0.5 suggests meaningful active management edge.

# Q: Why is Deflated Sharpe lower than Sharpe?
# A: It corrects for multiple testing bias.
#    This is GOOD — means the result is more robust.
#    If DSR is still > 0.5, you likely have real alpha.

# STEP 9: Next Steps
# ─────────────────────────────────────────────────────────────────────────────

# Option A: Use in production
#   1. Version control: Save model_registry.json + model_registry.pkl
#   2. Monitor: Track alpha/Sharpe monthly
#   3. Retrain: Every quarter with latest data
#   4. Report: Export metrics monthly for stakeholders

# Option B: Further research
#   1. Check SHAP explanations (which features drive returns?)
#   2. Test other covariance methods (shrinkage, DCC)
#   3. Optimize Kelly fraction (currently 0.5x)
#   4. Test different rebalance frequencies (currently 5 days)

# Option C: Deploy to frontend
#   1. Save equity curves to database
#   2. Expose metrics via API
#   3. Create live dashboard with daily updates
#   4. Set up alerts for drawdown threshold

# ─────────────────────────────────────────────────────────────────────────────
# That's it! You're ready to go.
# See README_ENHANCEMENTS.md for detailed documentation.
# ─────────────────────────────────────────────────────────────────────────────
