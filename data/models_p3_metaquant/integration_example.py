"""
Integration Example: Complete Institutional-Grade Pipeline
Demonstrates using evaluation_metrics.py, report_exporter.py, and HRP+Glasso together
for producing final reports with all industry-standard metrics and visualizations.

USAGE:
    python integration_example.py
    
This script:
1. Loads portfolio returns and benchmark
2. Computes Jensen's Alpha, Beta, Information Ratio
3. Calculates Deflated Sharpe Ratio
4. Generates comprehensive reports
5. Exports all outputs in production-ready formats
"""

import numpy as np
import pandas as pd
import pickle
from pathlib import Path
import json
import sys

# Import our institutional modules
from evaluation_metrics import PerformanceMetrics, compare_strategies
from report_exporter import ReportExporter


def load_portfolio_data(data_dir: Path = Path('.')):
    """Load all portfolio and benchmark data."""
    print("Loading portfolio data...")
    
    # Portfolio returns from HRP backtest
    portfolio_returns = pd.read_parquet(data_dir / 'hrp_glasso_equity_curves.parquet')
    portfolio_rets = portfolio_returns['HRP_Glasso'].pct_change().dropna()
    
    # Benchmark (S&P 500 or equal-weight market)
    benchmark_rets = portfolio_returns['Equal_Weight'].pct_change().dropna()
    
    # Load weights log
    weights_log = pd.read_parquet(data_dir / 'hrp_glasso_weights_history.parquet')
    
    # Load performance metrics
    performance_metrics = pd.read_csv(data_dir / 'hrp_glasso_performance_metrics.csv', index_col=0)
    
    return portfolio_rets, benchmark_rets, weights_log, performance_metrics


def compute_institutional_metrics(
    portfolio_returns: pd.Series,
    benchmark_returns: pd.Series,
    strategy_name: str = 'HRP+Glasso+Meta+Kelly+Regime'
) -> dict:
    """
    Compute complete institutional metrics including:
    - Jensen's Alpha
    - Beta
    - Information Ratio
    - Deflated Sharpe Ratio
    - Full performance suite
    """
    print(f"\nComputing institutional metrics for {strategy_name}...")
    
    metrics = PerformanceMetrics(
        returns=portfolio_returns,
        benchmark_returns=benchmark_returns,
        risk_free_rate=0.02,
        periods_per_year=252
    )
    
    # Generate full report
    full_report = metrics.full_report()
    
    # Additional CAPM metrics
    print(f"  ✓ Beta: {metrics.beta():.4f}")
    print(f"  ✓ Jensen's Alpha: {metrics.jensen_alpha()*100:.3f}%")
    print(f"  ✓ Information Ratio: {metrics.information_ratio():.4f}")
    print(f"  ✓ Tracking Error: {metrics.tracking_error()*100:.3f}%")
    print(f"  ✓ Sharpe Ratio: {metrics.sharpe_ratio():.4f}")
    print(f"  ✓ Deflated Sharpe: {metrics.deflated_sharpe_ratio():.4f}")
    print(f"  ✓ Sharpe p-value: {metrics.sharpe_pvalue():.6f}")
    
    return full_report


def export_all_reports(\n    portfolio_returns: pd.Series,\n    benchmark_returns: pd.Series,\n    portfolio_equity: pd.Series,\n    other_strategies: dict,\n    metrics_report: dict,\n    output_dir: Path = Path('.'),\n    tag: str = 'hrp_glasso'\n):\n    \"\"\"\n    Export complete report suite using ReportExporter.\n    \n    Outputs:\n    - Equity curves (CSV, Parquet, PNG, Excel)\n    - DSR metrics (JSON, CSV, PNG)\n    - Comparison dashboards (Excel, PNG)\n    - Manifest of all exports\n    \"\"\"\n    print(f\"\\nExporting reports to {output_dir}...\")\n    \n    exporter = ReportExporter(output_dir=output_dir)\n    all_exports = {}\n    \n    # 1. Save equity curves\n    print(\"  → Saving equity curves...\")\n    strategies = {\n        'HRP+Glasso+Meta+Kelly+Regime': portfolio_returns,\n        **other_strategies\n    }\n    equity_curves_exports = exporter.save_equity_curves(\n        strategies=strategies,\n        benchmark=benchmark_returns,\n        tag=tag\n    )\n    all_exports['equity_curves'] = equity_curves_exports\n    print(f\"     Saved as: Parquet, CSV, PNG, Excel\")\n    \n    # 2. Save DSR metrics\n    print(\"  → Saving DSR & statistical metrics...\")\n    dsr_exports = exporter.save_dsr_metrics(\n        metrics_dict=metrics_report,\n        strategy_name=tag\n    )\n    all_exports['dsr_metrics'] = dsr_exports\n    print(f\"     Saved as: JSON, CSV, PNG\")\n    \n    # 3. Save SHAP summary (if available)\n    print(\"  → Generating SHAP importance charts...\")\n    try:\n        # Load SHAP from model if available\n        with open(output_dir / 'shap_values.pkl', 'rb') as f:\n            shap_data = pickle.load(f)\n        \n        shap_exports = exporter.save_shap_summary(\n            shap_values=shap_data['values'],\n            feature_names=shap_data['feature_names'],\n            tag=tag\n        )\n        all_exports['shap'] = shap_exports\n        print(f\"     Saved as: CSV, JSON, PNG\")\n    except FileNotFoundError:\n        print(f\"     (No SHAP data found, skipping)\")\n    \n    # 4. Generate comparison dashboard\n    print(\"  → Creating comparison dashboard...\")\n    equity_df = pd.DataFrame({\n        'HRP+Glasso': (1 + portfolio_returns).cumprod(),\n        **{name: (1 + ret).cumprod() for name, ret in other_strategies.items()}\n    })\n    \n    comparison_exports = exporter.save_comparison_dashboard(\n        comparison_df=None,  # Would pass performance comparison here\n        equity_curves=equity_df,\n        title='Institutional HRP Portfolio with Graphical Lasso'\n    )\n    all_exports['dashboard'] = comparison_exports\n    print(f\"     Saved as: Excel, PNG\")\n    \n    # 5. Generate manifest\n    print(\"  → Generating export manifest...\")\n    manifest_path = exporter.generate_manifest(all_exports)\n    print(f\"     Manifest: {manifest_path}\")\n    \n    # Summary\n    print(\"\\n\" + \"=\"*80)\n    print(\"EXPORT SUMMARY\")\n    print(\"=\"*80)\n    total_files = sum(len(v) for v in all_exports.values())\n    print(f\"Total exports: {total_files} files\")\n    print(f\"Output directory: {output_dir}\")\n    print(f\"Timestamp: {exporter.timestamp}\")\n    print(\"\\nFile types:\")\n    for export_type, paths_dict in all_exports.items():\n        print(f\"  {export_type.replace('_', ' ').title()}:\")\n        for fmt, path in paths_dict.items():\n            print(f\"    - {path.name}\")\n    print(\"=\"*80)\n    \n    return all_exports, manifest_path


def create_executive_summary(\n    metrics_report: dict,\n    output_dir: Path = Path('.')\n) -> Path:\n    \"\"\"\n    Create an executive summary document.\n    \"\"\"\n    print(\"\\nGenerating executive summary...\")\n    \n    summary = f\"\"\"\nEXECUTIVE SUMMARY\n{'='*80}\nInstitutional-Grade HRP Portfolio with Graphical Lasso\n\nKEY PERFORMANCE METRICS\n{'-'*80}\n\nReturn & Risk:\n  Annual Return:              {metrics_report.get('Annual Return', 'N/A')}\n  Annual Volatility:          {metrics_report.get('Annual Volatility', 'N/A')}\n  Maximum Drawdown:           {metrics_report.get('Max Drawdown', 'N/A')}\n  Profit Factor:              {metrics_report.get('Profit Factor', 'N/A')}\n  Win Rate:                   {metrics_report.get('Win Rate', 'N/A')}\n\nRisk-Adjusted Returns:\n  Sharpe Ratio:               {metrics_report.get('Sharpe Ratio', 'N/A')}\n  Sortino Ratio:              {metrics_report.get('Sortino Ratio', 'N/A')}\n  Calmar Ratio:               {metrics_report.get('Calmar Ratio', 'N/A')}\n  \nCABM & Active Management:\n  Beta:                       {metrics_report.get('Beta', 'N/A')}\n  Jensen's Alpha:             {metrics_report.get(\"Jensen's Alpha\", 'N/A')}\n  Information Ratio:          {metrics_report.get('Information Ratio', 'N/A')}\n  Tracking Error:             {metrics_report.get('Tracking Error', 'N/A')}\n\nStatistical Significance:\n  Deflated Sharpe Ratio:      {metrics_report.get('Deflated Sharpe', 'N/A')}\n  Sharpe p-value:             {metrics_report.get('Sharpe p-value', 'N/A')}\n  Observations:               {metrics_report.get('Observations', 'N/A')}\n\nDownside Risk:\n  Value at Risk (95%):        {metrics_report.get('VaR (95%)', 'N/A')}\n  Conditional VaR (95%):      {metrics_report.get('CVaR (95%)', 'N/A')}\n\n{'-'*80}\nMETHODOLOGY NOTES\n{'-'*80}\n\nGraphical Lasso Covariance Estimation:\n  - L1-regularized sparse inverse covariance estimation\n  - Removes spurious correlations via shrinkage\n  - Distance metric based on partial correlations\n  - More robust than standard empirical covariance\n\nHierarchical Risk Parity (HRP):\n  - Hierarchical clustering via Ward's method on partial correlation distance\n  - Recursive bisection for allocation inversely proportional to cluster variance\n  - No matrix inversion required (numerically stable)\n  \nKelly Sizing & Risk Constraints:\n  - Fractional Kelly (0.5x) applied using P(Success) from meta-model\n  - Regime-conditional leverage ({0: 1.0, 1: 0.7, 2: 0.4})\n  - Position limits: 15% max, 0.1% min\n  - Daily transaction cost: 5 bps one-way\n\nPortfolio Signals:\n  - Ensemble of LightGBM models (momentum, volatility, technical)\n  - Conditioned on meta-model predicted success probability\n  - Rebalanced every 5 trading days\n  - Cross-validated walk-forward evaluation\n\n{'-'*80}\nFILES & ARTIFACTS\n{'-'*80}\n\nThis export includes:\n  - Equity curves (Parquet, CSV, Excel, PNG)\n  - Performance metrics with DSR significance tests\n  - SHAP feature importance explanations (if model available)\n  - Comparison dashboards vs. benchmarks\n  - Complete export manifest\n\nFor institutional reporting and presentations.\n\"\"\"\n    \n    summary_path = output_dir / 'EXECUTIVE_SUMMARY.txt'\n    with open(summary_path, 'w') as f:\n        f.write(summary)\n    \n    print(f\"Summary saved: {summary_path}\")\n    return summary_path\n\n\ndef main():\n    \"\"\"Main execution flow.\"\"\"\n    print(\"\\n\" + \"=\"*80)\n    print(\"INSTITUTIONAL QUANT PIPELINE\")\n    print(\"Evaluation Metrics + HRP Glasso + Report Exporter\")\n    print(\"=\"*80)\n    \n    # Configuration\n    data_dir = Path('.')  # Current directory (models_p3_metaquant)\n    output_dir = data_dir / 'reports'\n    output_dir.mkdir(parents=True, exist_ok=True)\n    \n    # 1. Load data\n    try:\n        portfolio_rets, benchmark_rets, weights_log, perf_metrics = load_portfolio_data(data_dir)\n    except Exception as e:\n        print(f\"ERROR loading data: {e}\")\n        print(\"Ensure HRP+Glasso notebook has been executed.\")\n        return\n    \n    # 2. Compute institutional metrics\n    metrics_report = compute_institutional_metrics(\n        portfolio_returns=portfolio_rets,\n        benchmark_returns=benchmark_rets\n    )\n    \n    # 3. Additional strategy comparison\n    other_strategies = {\n        'Naive_TopN': benchmark_rets,  # Placeholder; would load actual naive returns\n    }\n    \n    # 4. Export all reports\n    portfolio_equity = (1 + portfolio_rets).cumprod()\n    all_exports, manifest_path = export_all_reports(\n        portfolio_returns=portfolio_rets,\n        benchmark_returns=benchmark_rets,\n        portfolio_equity=portfolio_equity,\n        other_strategies=other_strategies,\n        metrics_report=metrics_report,\n        output_dir=output_dir,\n        tag='hrp_glasso_full'\n    )\n    \n    # 5. Create executive summary\n    create_executive_summary(metrics_report, output_dir)\n    \n    print(\"\\n✓ Pipeline complete!\")\n    print(f\"\\nAll outputs saved to: {output_dir}\")\n    print(f\"Ready for institutional reporting and presentations.\")\n\n\nif __name__ == '__main__':\n    main()\n