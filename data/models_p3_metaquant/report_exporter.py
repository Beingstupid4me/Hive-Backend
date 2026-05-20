"""
Final Output Exporter for Report Generation
Saves equity curves, SHAP explanations, DSR metrics, and supporting artifacts
in production-ready formats for institutional reporting and presentations.
"""

import numpy as np
import pandas as pd
import json
import pickle
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from datetime import datetime
import warnings

warnings.filterwarnings('ignore')


class ReportExporter:
    """
    Institutional-grade report exporter.
    
    Outputs:
    - Equity curves (CSV, Parquet, PNG)
    - SHAP summary charts (PNG, JSON)
    - DSR metrics (JSON, CSV)
    - Performance dashboards (PNG)
    - Comparison tables (Excel, CSV, HTML)
    """
    
    def __init__(self, output_dir: Path = Path('.')):
        """Initialize exporter with output directory."""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
    # ──────────────────────────────────────────────────────────────────────────
    # EQUITY CURVES & TIME SERIES
    # ──────────────────────────────────────────────────────────────────────────
    
    def save_equity_curves(
        self,
        strategies: Dict[str, pd.Series],
        benchmark: Optional[pd.Series] = None,
        tag: str = 'portfolio'
    ) -> Dict[str, Path]:
        """
        Save equity curves in multiple formats.
        
        Args:
            strategies: {strategy_name: returns_series}
            benchmark: Optional benchmark returns
            tag: Prefix for output files
        
        Returns:
            Dict mapping format to file path
        """
        # Construct cumulative returns
        equity_df = pd.DataFrame()
        for name, returns in strategies.items():
            equity_df[name] = (1 + returns).cumprod()
        
        if benchmark is not None:
            equity_df['Benchmark'] = (1 + benchmark).cumprod()
        
        paths = {}
        
        # Save as Parquet (efficient for large datasets)
        parquet_path = self.output_dir / f'{tag}_equity_curves_{self.timestamp}.parquet'
        equity_df.to_parquet(parquet_path)
        paths['parquet'] = parquet_path
        
        # Save as CSV (universal format)
        csv_path = self.output_dir / f'{tag}_equity_curves_{self.timestamp}.csv'
        equity_df.to_csv(csv_path)
        paths['csv'] = csv_path
        
        # Save as Excel with formatting
        excel_path = self.output_dir / f'{tag}_equity_curves_{self.timestamp}.xlsx'
        with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
            equity_df.to_excel(writer, sheet_name='Equity Curves')
            
            # Add conditional formatting
            workbook = writer.book
            worksheet = writer.sheets['Equity Curves']
            worksheet.column_dimensions['A'].width = 15
            for col in range(2, len(equity_df.columns) + 2):
                worksheet.column_dimensions[chr(64 + col)].width = 18
        
        paths['excel'] = excel_path
        
        # Generate PNG visualization
        fig, ax = plt.subplots(figsize=(14, 7))
        for col in equity_df.columns:
            ax.plot(equity_df.index, equity_df[col], linewidth=2.5, label=col)
        
        ax.set_title(f'Equity Curves — {tag.title()}', fontsize=14, fontweight='bold')
        ax.set_xlabel('Date', fontsize=11)
        ax.set_ylabel('Cumulative Return Index', fontsize=11)
        ax.legend(loc='upper left', fontsize=10)
        ax.grid(True, alpha=0.3)
        ax.axhline(y=1, color='black', linestyle='--', alpha=0.5)
        
        png_path = self.output_dir / f'{tag}_equity_curves_{self.timestamp}.png'
        plt.tight_layout()
        plt.savefig(png_path, dpi=300, bbox_inches='tight')
        plt.close()
        paths['png'] = png_path
        
        return paths
    
    # ──────────────────────────────────────────────────────────────────────────
    # SHAP & INTERPRETABILITY
    # ──────────────────────────────────────────────────────────────────────────
    
    def save_shap_summary(
        self,
        shap_values: np.ndarray,
        feature_names: List[str],
        tag: str = 'model'
    ) -> Dict[str, Path]:
        """
        Save SHAP feature importance summary.
        
        Args:
            shap_values: SHAP values array (n_samples, n_features)
            feature_names: List of feature names
            tag: Prefix for output files
        
        Returns:
            Dict mapping format to file path
        """
        paths = {}
        
        # Mean absolute SHAP values (feature importance)
        mean_abs_shap = np.abs(shap_values).mean(axis=0)
        shap_df = pd.DataFrame({
            'Feature': feature_names,
            'Mean_Abs_SHAP': mean_abs_shap,
            'Rank': np.argsort(-mean_abs_shap) + 1
        }).sort_values('Mean_Abs_SHAP', ascending=False)
        
        # Save as CSV
        csv_path = self.output_dir / f'{tag}_shap_summary_{self.timestamp}.csv'
        shap_df.to_csv(csv_path, index=False)
        paths['csv'] = csv_path
        
        # Save as JSON
        json_path = self.output_dir / f'{tag}_shap_summary_{self.timestamp}.json'
        shap_json = {\n            'timestamp': self.timestamp,\n            'features': shap_df.to_dict(orient='records')\n        }\n        with open(json_path, 'w') as f:
            json.dump(shap_json, f, indent=2)
        paths['json'] = json_path
        
        # Generate PNG bar chart
        fig, ax = plt.subplots(figsize=(12, 8))
        colors = plt.cm.viridis(np.linspace(0, 1, len(shap_df[:20])))\n        ax.barh(range(len(shap_df[:20])), shap_df['Mean_Abs_SHAP'].iloc[:20].values, color=colors)\n        ax.set_yticks(range(len(shap_df[:20])))\n        ax.set_yticklabels(shap_df['Feature'].iloc[:20].values)\n        ax.set_xlabel('Mean |SHAP| Value', fontsize=11, fontweight='bold')\n        ax.set_title(f'SHAP Feature Importance — Top 20 Features ({tag})', \n                     fontsize=13, fontweight='bold')\n        ax.grid(True, alpha=0.3, axis='x')\n        \n        png_path = self.output_dir / f'{tag}_shap_importance_{self.timestamp}.png'\n        plt.tight_layout()\n        plt.savefig(png_path, dpi=300, bbox_inches='tight')\n        plt.close()\n        paths['png'] = png_path\n        \n        return paths\n    
    def save_shap_waterfall(\n        self,\n        shap_values: np.ndarray,\n        feature_names: List[str],\n        base_value: float,\n        sample_idx: int = 0,\n        tag: str = 'model'\n    ) -> Path:\n        \"\"\"\n        Save SHAP waterfall plot for individual prediction.\n        \n        Args:\n            shap_values: SHAP values\n            feature_names: Feature names\n            base_value: Model base value (expected value)\n            sample_idx: Index of sample to explain\n            tag: File prefix\n        \n        Returns:\n            Path to saved PNG\n        \"\"\"\n        # Get top features by SHAP magnitude\n        sample_shaps = shap_values[sample_idx]\n        top_indices = np.argsort(np.abs(sample_shaps))[-15:][::-1]\n        \n        fig, ax = plt.subplots(figsize=(12, 8))\n        \n        # Waterfall effect\n        x_pos = 0\n        current_value = base_value\n        values = [base_value]\n        labels = ['Base']\n        colors_list = []\n        \n        for idx in top_indices:\n            shap_val = sample_shaps[idx]\n            if shap_val > 0:\n                colors_list.append('#d62728')  # red for positive\n            else:\n                colors_list.append('#1f77b4')  # blue for negative\n            values.append(shap_val)\n            labels.append(feature_names[idx][:30])\n            current_value += shap_val\n        \n        values.append(current_value - base_value)\n        labels.append('Model Output')\n        colors_list.append('#2ca02c')\n        \n        # Plot waterfall\n        x = np.arange(len(labels))\n        cumsum = np.cumsum([base_value] + values[:-1])\n        ax.bar(x[:-1], values[:-1], bottom=cumsum[:-1], color=colors_list[:-1], edgecolor='black', linewidth=0.5)\n        ax.bar(x[-1], values[-1], bottom=0, color=colors_list[-1], edgecolor='black', linewidth=0.5)\n        \n        ax.axhline(y=0, color='black', linestyle='-', linewidth=1)\n        ax.set_xticks(x)\n        ax.set_xticklabels(labels, rotation=45, ha='right', fontsize=9)\n        ax.set_ylabel('SHAP Value (Impact on Output)', fontsize=11, fontweight='bold')\n        ax.set_title(f'SHAP Waterfall — Prediction Explanation ({tag}, Sample {sample_idx})',\n                     fontsize=13, fontweight='bold')\n        ax.grid(True, alpha=0.3, axis='y')\n        \n        png_path = self.output_dir / f'{tag}_shap_waterfall_{self.timestamp}.png'\n        plt.tight_layout()\n        plt.savefig(png_path, dpi=300, bbox_inches='tight')\n        plt.close()\n        \n        return png_path\n    \n    # ──────────────────────────────────────────────────────────────────────────\n    # DSR & STATISTICAL SIGNIFICANCE\n    # ──────────────────────────────────────────────────────────────────────────\n    \n    def save_dsr_metrics(\n        self,\n        metrics_dict: Dict,\n        strategy_name: str = 'portfolio'\n    ) -> Dict[str, Path]:\n        \"\"\"\n        Save Deflated Sharpe Ratio and statistical significance metrics.\n        \n        Args:\n            metrics_dict: Dictionary of metrics (from PerformanceMetrics.full_report())\n            strategy_name: Strategy name for file prefix\n        \n        Returns:\n            Dict mapping format to file path\n        \"\"\"\n        paths = {}\n        \n        # Save as JSON\n        json_path = self.output_dir / f'{strategy_name}_dsr_metrics_{self.timestamp}.json'\n        with open(json_path, 'w') as f:\n            json.dump(metrics_dict, f, indent=2)\n        paths['json'] = json_path\n        \n        # Save as CSV\n        csv_path = self.output_dir / f'{strategy_name}_dsr_metrics_{self.timestamp}.csv'\n        metrics_df = pd.DataFrame([metrics_dict]).T\n        metrics_df.columns = ['Value']\n        metrics_df.to_csv(csv_path)\n        paths['csv'] = csv_path\n        \n        # Generate PDF-ready table PNG\n        fig, ax = plt.subplots(figsize=(10, 8))\n        ax.axis('off')\n        \n        table_data = []\n        for key, value in metrics_dict.items():\n            table_data.append([key, str(value)])\n        \n        table = ax.table(\n            cellText=table_data,\n            colLabels=['Metric', 'Value'],\n            cellLoc='left',\n            loc='center',\n            colWidths=[0.6, 0.4]\n        )\n        table.auto_set_font_size(False)\n        table.set_fontsize(10)\n        table.scale(1, 2)\n        \n        # Style header\n        for i in range(2):\n            table[(0, i)].set_facecolor('#40466e')\n            table[(0, i)].set_text_props(weight='bold', color='white')\n        \n        # Alternate row colors\n        for i in range(1, len(table_data) + 1):\n            for j in range(2):\n                if i % 2 == 0:\n                    table[(i, j)].set_facecolor('#f0f0f0')\n        \n        plt.title(f'{strategy_name.title()} — Deflated Sharpe & Performance Metrics',\n                  fontsize=13, fontweight='bold', pad=20)\n        \n        png_path = self.output_dir / f'{strategy_name}_dsr_metrics_{self.timestamp}.png'\n        plt.savefig(png_path, dpi=300, bbox_inches='tight')\n        plt.close()\n        paths['png'] = png_path\n        \n        return paths\n    \n    # ──────────────────────────────────────────────────────────────────────────\n    # PERFORMANCE COMPARISON DASHBOARDS\n    # ──────────────────────────────────────────────────────────────────────────\n    \n    def save_comparison_dashboard(\n        self,\n        comparison_df: pd.DataFrame,\n        equity_curves: pd.DataFrame,\n        title: str = 'Strategy Comparison'\n    ) -> Dict[str, Path]:\n        \"\"\"\n        Generate comprehensive comparison dashboard.\n        \n        Args:\n            comparison_df: Performance metrics by strategy (from compare_strategies)\n            equity_curves: Equity curves (cumulative returns by date/strategy)\n            title: Dashboard title\n        \n        Returns:\n            Dict mapping format to file path\n        \"\"\"\n        paths = {}\n        \n        # Save comparison table as Excel\n        excel_path = self.output_dir / f'comparison_dashboard_{self.timestamp}.xlsx'\n        with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:\n            comparison_df.to_excel(writer, sheet_name='Performance')\n            equity_curves.to_excel(writer, sheet_name='Equity Curves')\n        paths['excel'] = excel_path\n        \n        # Create multi-panel dashboard PNG\n        fig = plt.figure(figsize=(18, 12))\n        gs = gridspec.GridSpec(3, 2, figure=fig, hspace=0.35, wspace=0.3)\n        \n        # Panel 1: Equity curves\n        ax1 = fig.add_subplot(gs[0, :])\n        for col in equity_curves.columns:\n            ax1.plot(equity_curves.index, equity_curves[col], linewidth=2.5, label=col)\n        ax1.set_title(f'{title} — Cumulative Returns', fontsize=13, fontweight='bold')\n        ax1.set_ylabel('Cumulative Return Index', fontsize=10)\n        ax1.legend(loc='upper left', fontsize=9)\n        ax1.grid(True, alpha=0.3)\n        ax1.axhline(y=1, color='black', linestyle='--', alpha=0.5)\n        \n        # Panel 2: Return distribution\n        ax2 = fig.add_subplot(gs[1, 0])\n        daily_rets = equity_curves.pct_change().dropna()\n        daily_rets.plot(kind='box', ax=ax2)\n        ax2.set_title('Daily Return Distribution', fontsize=12, fontweight='bold')\n        ax2.set_ylabel('Daily Return (%)', fontsize=10)\n        ax2.grid(True, alpha=0.3, axis='y')\n        \n        # Panel 3: Key metrics\n        ax3 = fig.add_subplot(gs[1, 1])\n        ax3.axis('off')\n        \n        key_metrics = comparison_df.loc[['Sharpe', 'Annual Return', 'Max Drawdown', 'Sortino']]\n        table_data = []\n        for idx in key_metrics.index:\n            for col in key_metrics.columns:\n                table_data.append([f\"{idx} ({col})\", str(key_metrics.loc[idx, col])])\n        \n        table = ax3.table(cellText=table_data, colLabels=['Metric', 'Value'],\n                         cellLoc='left', loc='center', colWidths=[0.6, 0.4])\n        table.auto_set_font_size(False)\n        table.set_fontsize(9)\n        table.scale(1, 1.8)\n        \n        for i in range(2):\n            table[(0, i)].set_facecolor('#40466e')\n            table[(0, i)].set_text_props(weight='bold', color='white')\n        \n        ax3.set_title('Key Performance Metrics', fontsize=12, fontweight='bold', pad=10)\n        \n        # Panel 4: Drawdown comparison\n        ax4 = fig.add_subplot(gs[2, :])\n        for col in equity_curves.columns:\n            running_max = equity_curves[col].expanding().max()\n            drawdown = (equity_curves[col] - running_max) / running_max * 100\n            ax4.fill_between(drawdown.index, drawdown, 0, alpha=0.3, label=col)\n        \n        ax4.set_title('Drawdown Profile', fontsize=12, fontweight='bold')\n        ax4.set_ylabel('Drawdown (%)', fontsize=10)\n        ax4.set_xlabel('Date', fontsize=10)\n        ax4.legend(loc='lower left', fontsize=9)\n        ax4.grid(True, alpha=0.3)\n        \n        plt.suptitle(title, fontsize=15, fontweight='bold', y=0.995)\n        \n        png_path = self.output_dir / f'comparison_dashboard_{self.timestamp}.png'\n        plt.savefig(png_path, dpi=300, bbox_inches='tight')\n        plt.close()\n        paths['png'] = png_path\n        \n        return paths\n    \n    # ──────────────────────────────────────────────────────────────────────────\n    # SUMMARY & MANIFEST\n    # ──────────────────────────────────────────────────────────────────────────\n    \n    def generate_manifest(self, all_exports: Dict[str, Dict]) -> Path:\n        \"\"\"\n        Generate manifest of all exported files.\n        \n        Args:\n            all_exports: Dict of all export operations\n        \n        Returns:\n            Path to manifest JSON\n        \"\"\"\n        manifest = {\n            'timestamp': self.timestamp,\n            'export_summary': {},\n            'files': {}\n        }\n        \n        for export_type, paths_dict in all_exports.items():\n            manifest['export_summary'][export_type] = {\n                'formats': list(paths_dict.keys()),\n                'count': len(paths_dict)\n            }\n            \n            for fmt, path in paths_dict.items():\n                manifest['files'][str(path)] = {\n                    'type': export_type,\n                    'format': fmt,\n                    'size_mb': path.stat().st_size / 1e6 if path.exists() else 0\n                }\n        \n        manifest_path = self.output_dir / f'export_manifest_{self.timestamp}.json'\n        with open(manifest_path, 'w') as f:\n            json.dump(manifest, f, indent=2)\n        \n        return manifest_path\n\n\nif __name__ == '__main__':\n    print(\"✓ Report exporter module loaded\")\n