"""
INSTITUTIONAL QUANT ENHANCEMENTS
New Modules for Production-Ready Analysis & Reporting
================================================================================

Three new production-grade modules have been added to your quantitative pipeline:

1. evaluation_metrics.py     — Industry-standard performance metrics
2. 05_hrp_glasso_portfolio.ipynb — HRP with Graphical Lasso covariance
3. report_exporter.py        — Institutional-grade report generation

================================================================================
1. EVALUATION_METRICS.PY
================================================================================

A comprehensive PerformanceMetrics class implementing institutional standards
from AQR, Two Sigma, Renaissance caliber funds.

KEY FEATURES:

  ✓ Jensen's Alpha              Risk-adjusted excess return vs. CAPM
  ✓ Beta                        Systematic risk (market sensitivity)
  ✓ Information Ratio           Alpha per unit of active risk
  ✓ Tracking Error              Deviation from benchmark
  ✓ Deflated Sharpe Ratio       Corrects for multiple testing bias
  ✓ Sharpe p-value              Statistical significance of alpha
  ✓ Bootstrap confidence intervals — Non-parametric CI estimation
  
  + All standard metrics:
    - Annual return, volatility
    - Sharpe, Sortino, Calmar ratios
    - Max drawdown, profit factor, win rate
    - VaR, CVaR (tail risk)

USAGE EXAMPLE:

    from evaluation_metrics import PerformanceMetrics, compare_strategies
    
    # Single strategy
    metrics = PerformanceMetrics(
        returns=portfolio_daily_returns,
        benchmark_returns=spy_daily_returns,
        risk_free_rate=0.02  # 2% annual
    )
    
    # Print full report
    report = metrics.full_report()
    for metric, value in report.items():
        print(f"{metric}: {value}")
    
    # Access specific metrics
    alpha = metrics.jensen_alpha()              # Annual Jensen's Alpha
    beta = metrics.beta()                       # Portfolio beta
    ir = metrics.information_ratio()            # Information ratio
    dsr = metrics.deflated_sharpe_ratio()       # Deflated Sharpe (corrected for overfitting)
    p_val = metrics.sharpe_pvalue()             # Is Sharpe statistically significant?
    
    # Bootstrap confidence intervals
    lower_ci, upper_ci = metrics.bootstrap_ci(
        metric_fn=lambda r: r.mean() * 252,
        n_bootstrap=1000,
        ci=0.95
    )
    
    # Compare multiple strategies
    strategies = {
        'HRP+Glasso': portfolio_returns_1,
        'Standard HRP': portfolio_returns_2,
        'Naive Equal Weight': portfolio_returns_3
    }
    comparison = compare_strategies(strategies, benchmark=benchmark_returns)
    print(comparison)  # Side-by-side metrics


INTERPRETATION GUIDE:

  Jensen's Alpha (α):
    α > 0%   : Outperformance (beating CAPM prediction)
    α < 0%   : Underperformance (below CAPM prediction)
    α = 0%   : Fairly priced relative to systematic risk
    
  Beta (β):
    β = 1.0  : Moves exactly with market
    β > 1.0  : More volatile than market (amplifies moves)
    β < 1.0  : Less volatile than market (dampens moves)
    β = 0    : Market-neutral strategy
    
  Information Ratio (IR):
    IR > 1.0 : Excellent active manager (1% alpha per 1% tracking error)
    IR > 0.5 : Good active manager
    IR < 0   : Underperformance relative to benchmark
    
  Deflated Sharpe Ratio (DSR):
    DSR > original Sharpe  : Robust result, not likely overfitting
    DSR << original Sharpe : Possible backtest bias, multiple testing
    DSR < 0.0              : Likely spurious alpha
    
  Sharpe p-value:
    p < 0.05 : Statistically significant excess return
    p ≥ 0.05 : Cannot reject null hypothesis of no alpha


KEY PARAMETERS:

  - risk_free_rate (float): Annual risk-free rate, default 2%
  - periods_per_year (int): Trading periods per year, default 252 (daily)
  - benchmark_returns: Optional for CAPM metrics (Alpha, Beta, IR)
  - n_trials: Number of trials for DSR (accounts for overfitting)


FORMULAS:

  Jensen's Alpha:
    α = r_p - [r_f + β(r_m - r_f)]
    
  Beta:
    β = Cov(r_p, r_m) / Var(r_m)
    
  Information Ratio:
    IR = (r_p - r_b) / TE
    where TE = std(r_p - r_b)
    
  Deflated Sharpe:
    DSR ≈ Sharpe × sqrt(1 - (π/2)^0.5 × ν/n × corr)
    Corrects for multiple strategy testing


================================================================================
2. 05_HRP_GLASSO_PORTFOLIO.IPYNB
================================================================================

Enhanced HRP portfolio implementation using Graphical Lasso for robust
covariance estimation. Trades off complexity for numerical stability and
better out-of-sample performance.

KEY IMPROVEMENTS OVER STANDARD HRP:

  ✓ Graphical Lasso (L1-regularized) covariance estimation
    - Shrinks spurious correlations
    - Produces sparse, stable precision matrix
    - Automatically selects regularization via cross-validation
    
  ✓ Partial correlation distance metric
    - Removes confounding effects of other variables
    - More robust than standard correlation-based distance
    
  ✓ All standard HRP benefits maintained:
    - No matrix inversion (numerically stable)
    - Hierarchical clustering (Ward's method)
    - Recursive bisection allocation


METHODOLOGY:

  1. COVARIANCE ESTIMATION
     Input:  Returns matrix (n_samples × n_assets)
     Method: GraphicalLassoCV (scikit-learn)
               - Solves: min_Θ { -log det(Θ) + trace(SΘ) + λ||Θ||_1 }
               - Θ = precision matrix (inverse covariance)
               - λ selected via K-fold cross-validation
     Output: Sparse precision matrix (more stable than empirical cov)
  
  2. DISTANCE CALCULATION
     From precision matrix Θ, compute partial correlations:
     ρ_ij = -Θ_ij / sqrt(Θ_ii × Θ_jj)
     
     Then distance:
     D_ij = sqrt(0.5 × (1 - ρ_ij))
  
  3. CLUSTERING & ALLOCATION
     Same as standard HRP:
     - Hierarchical clustering on distance matrix
     - Quasi-diagonalization
     - Recursive bisection (allocate inversely proportional to variance)
  
  4. KELLY SIZING & CONSTRAINTS
     - Scale by P(Success) from meta-model
     - Apply regime-conditional leverage
     - Enforce position limits (max 15%, min 0.1%)


EXPECTED IMPROVEMENTS:

  - Better out-of-sample performance on small universes
  - Reduced false correlations (Glasso shrinkage)
  - More stable portfolio weights across rebalances
  - Better behavior in high-volatility regimes


EXECUTION:

  In Jupyter:
    jupyter notebook 05_hrp_glasso_portfolio.ipynb
    
  Or via terminal:
    python -m jupyter notebook 05_hrp_glasso_portfolio.ipynb


OUTPUTS:

  Files saved automatically:
  - hrp_glasso_equity_curves.parquet     Cumulative returns by strategy
  - hrp_glasso_performance_metrics.csv   Full metrics comparison
  - hrp_glasso_weights_history.parquet   Portfolio weight history
  - hrp_glasso_dsr_report.json          Deflated Sharpe report
  - hrp_glasso_dashboard.png            Multi-panel performance chart


PARAMETERS TO TUNE:

  TOP_N             = 30       # Candidates from alpha model
  PSUCCESS_MIN      = 0.52     # Min P(Success) threshold
  COV_LOOKBACK      = 63       # Days of history for covariance
  MAX_WEIGHT        = 0.15     # Max position size
  KELLY_FRACTION    = 0.5      # Half-Kelly for safety
  REBAL_DAYS        = 5        # Rebalance frequency


SCIENTIFIC REFERENCES:

  - Graphical Lasso: Friedman et al., "Sparse inverse covariance estimation
    with the graphical lasso" (2008)
  - HRP: López de Prado, "Building Diversified Portfolios that Outperform"
    (2016)
  - Partial correlation distance: Mantegna, "Hierarchical structure in
    financial markets" (1999)


================================================================================
3. REPORT_EXPORTER.PY
================================================================================

Production-ready report generation. Creates institutional-grade outputs
in multiple formats (Parquet, CSV, PNG, Excel, JSON) suitable for
presentations, regulatory reports, and client deliverables.

KEY FEATURES:

  ✓ Equity curves in multiple formats
    - Parquet (efficient storage)
    - CSV (universal compatibility)
    - Excel (formatted, easy to share)
    - PNG (presentations, publications)
    
  ✓ SHAP explanations
    - Feature importance bar charts
    - Waterfall plots (individual predictions)
    - JSON export (data science workflows)
    
  ✓ Statistical metrics
    - DSR (deflated Sharpe) reports
    - Formatted metric tables
    - Publication-ready PNGs
    
  ✓ Comparison dashboards
    - Multi-panel equity curves
    - Return distributions
    - Drawdown profiles
    - Key metrics tables


USAGE EXAMPLE:

    from report_exporter import ReportExporter
    
    exporter = ReportExporter(output_dir=Path('./reports'))
    
    # 1. Export equity curves
    strategies = {
        'HRP+Glasso': portfolio_returns_1,
        'Naive Equal Weight': portfolio_returns_2
    }
    equity_paths = exporter.save_equity_curves(
        strategies=strategies,
        benchmark=benchmark_returns,
        tag='hrp_comparison'
    )
    # Returns: {'parquet': Path(...), 'csv': Path(...), 'png': Path(...), 'excel': Path(...)}
    
    
    # 2. Export DSR metrics
    metrics_dict = {
        'Annual Return': '12.5%',
        'Sharpe Ratio': '1.25',
        'Deflated Sharpe': '0.95',
        'Beta': '0.85',
        'Jensen Alpha': '3.2%',
        'Information Ratio': '1.15'
    }
    dsr_paths = exporter.save_dsr_metrics(
        metrics_dict=metrics_dict,
        strategy_name='hrp_glasso'
    )
    # Returns: {'json': Path(...), 'csv': Path(...), 'png': Path(...)}
    
    
    # 3. Export SHAP explanations
    shap_paths = exporter.save_shap_summary(
        shap_values=shap_values_array,  # (n_samples, n_features)
        feature_names=feature_list,
        tag='lgb_ensemble'
    )
    # Returns: {'csv': Path(...), 'json': Path(...), 'png': Path(...)}
    
    
    # 4. Create comparison dashboard
    equity_df = pd.DataFrame({
        'Strategy A': (1 + returns_a).cumprod(),
        'Strategy B': (1 + returns_b).cumprod(),
        'Benchmark': (1 + returns_bench).cumprod()
    })
    dashboard_paths = exporter.save_comparison_dashboard(
        comparison_df=comparison_metrics,
        equity_curves=equity_df,
        title='Portfolio Optimization Results'
    )
    # Returns: {'excel': Path(...), 'png': Path(...)}
    
    
    # 5. Generate manifest
    all_exports = {
        'equity': equity_paths,
        'dsr': dsr_paths,
        'shap': shap_paths,
        'dashboard': dashboard_paths
    }
    manifest = exporter.generate_manifest(all_exports)
    # manifest.json contains all file metadata


OUTPUT DIRECTORY STRUCTURE:

    reports/
    ├── export_manifest_20240421_143022.json
    ├── hrp_glasso_equity_curves_20240421_143022.parquet
    ├── hrp_glasso_equity_curves_20240421_143022.csv
    ├── hrp_glasso_equity_curves_20240421_143022.xlsx
    ├── hrp_glasso_equity_curves_20240421_143022.png
    ├── hrp_glasso_dsr_metrics_20240421_143022.json
    ├── hrp_glasso_dsr_metrics_20240421_143022.csv
    ├── hrp_glasso_dsr_metrics_20240421_143022.png
    ├── lgb_ensemble_shap_summary_20240421_143022.csv
    ├── lgb_ensemble_shap_summary_20240421_143022.json
    ├── lgb_ensemble_shap_importance_20240421_143022.png
    ├── comparison_dashboard_20240421_143022.xlsx
    └── comparison_dashboard_20240421_143022.png


FORMAT SPECIFICATIONS:

  Parquet:  Apache Parquet (efficient, compressed, schema-preserving)
  CSV:      Standard comma-separated values (UTF-8)
  Excel:    XLSX format with formatting (colors, headers)
  PNG:      300 DPI publication-ready PNG images
  JSON:     Structured JSON with metadata


MANIFEST CONTENTS:

    {
      "timestamp": "20240421_143022",
      "export_summary": {
        "equity_curves": {
          "formats": ["parquet", "csv", "png", "excel"],
          "count": 4
        },
        "dsr_metrics": {
          "formats": ["json", "csv", "png"],
          "count": 3
        }
      },
      "files": {
        "hrp_glasso_equity_curves_...xlsx": {
          "type": "equity_curves",
          "format": "excel",
          "size_mb": 0.5
        },
        ...
      }
    }


================================================================================
INTEGRATION EXAMPLE
================================================================================

A complete example (`integration_example.py`) demonstrates the full workflow:

    python integration_example.py

This script:
  1. Loads HRP+Glasso portfolio results
  2. Computes all institutional metrics (Alpha, Beta, IR, DSR)
  3. Exports equity curves, metrics, and SHAP in all formats
  4. Generates comparison dashboard
  5. Creates executive summary
  6. Produces manifest

All outputs suitable for institutional reporting.


================================================================================
WORKFLOW RECOMMENDATIONS
================================================================================

TYPICAL USAGE SEQUENCE:

  1. RUN EXISTING PIPELINE
     - 01_feature_factory.ipynb         (features)
     - 02_alpha_models.ipynb             (signal models)
     - 03_meta_labeling.ipynb            (meta-model)
     - 04_regime_detection.ipynb         (regime state)
  
  2. RUN NEW HRP GLASSO
     - 05_hrp_glasso_portfolio.ipynb     (portfolio construction)
  
  3. ANALYZE & EXPORT
     - integration_example.py            (complete metrics & reports)
     OR
     - Jupyter: Run evaluation_metrics.py + report_exporter.py cells
  
  4. REVIEW OUTPUTS
     - Generated PNG dashboards
     - Excel performance comparison
     - DSR report (statistical significance)


FOR PRODUCTION DEPLOYMENT:

  1. Set random seed for reproducibility
  2. Log all hyperparameters (HRP parameters, Kelly fraction)
  3. Track model version and data version
  4. Store model registry (final_model_registry.json)
  5. Monitor drift: compare recent vs. historical metrics
  6. Export to shared reporting system (Excel → Tableau, BI tool, etc.)


================================================================================
REQUIREMENTS & DEPENDENCIES
================================================================================

Required packages (auto-included in base environment):
  - numpy, pandas, scipy
  - scikit-learn (for GraphicalLassoCV)
  - matplotlib, seaborn
  - openpyxl (for Excel export)

Already in your environment:
  - lightgbm (alpha models)
  - statsmodels (regime detection)

Installation if needed:
    pip install scikit-learn openpyxl


================================================================================
TROUBLESHOOTING
================================================================================

Q: "GraphicalLassoCV failing on small universes"
A: Glasso requires at least 30 observations and more features than samples.
   For <10 assets, use standard HRP (fallback automatic in notebook).

Q: "Memory error when exporting large equity curves"
A: Use Parquet format (compressed) instead of CSV. Or chunk data by year.

Q: "SHAP files not found"
A: SHAP export is optional. Notebook skips if shap_values.pkl doesn't exist.

Q: "Excel export permission denied"
A: Close Excel file before running export. Or save to different timestamp.

Q: "Sharpe p-value always < 0.05"
A: May indicate overfitting. Check Deflated Sharpe Ratio < original Sharpe.
   Run walk-forward validation to verify robustness.

Q: "DSR negative after deflation"
A: Result likely due to multiple testing bias. Consider ensemble approach
   or expand validation period.


================================================================================
CITATION & REFERENCES
================================================================================

These enhancements implement methods from:

  [1] López de Prado, M. (2016). Building Diversified Portfolios that
      Outperform. Journal of Portfolio Management, 42(4), 59-69.
  
  [2] Friedman, J., Hastie, T., Tibshirani, R. (2008). Sparse inverse
      covariance estimation with the graphical lasso. Biostatistics, 9(3).
  
  [3] Bailey, D.H., López de Prado, M. (2014). The Deflated Sharpe Ratio:
      Correcting for Selection Bias, Backtest Overfitting and Non-Normality.
      Journal of Portfolio Management, 40(5), 94-107.
  
  [4] Harvey, C.R., Liu, Y., Zhu, H. (2016). ... and the Cross-Section of
      Expected Returns. Review of Financial Studies, 29(1), 5-68.

"""

print("✓ Documentation loaded")
