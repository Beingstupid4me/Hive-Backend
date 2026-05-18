from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


class ArtifactRepository:
    def __init__(self, model_data_dir: Path) -> None:
        self.model_data_dir = model_data_dir
        self._csv_cache: dict[str, pd.DataFrame] = {}
        self._json_cache: dict[str, dict[str, Any]] = {}

    def _csv_path(self, name: str) -> Path:
        return self.model_data_dir / name

    def _json_path(self, name: str) -> Path:
        return self.model_data_dir / name

    def load_csv(self, name: str) -> pd.DataFrame:
        if name in self._csv_cache:
            return self._csv_cache[name].copy()

        path = self._csv_path(name)
        if not path.exists():
            df = pd.DataFrame()
            self._csv_cache[name] = df
            return df.copy()

        df = pd.read_csv(path)
        self._csv_cache[name] = df
        return df.copy()

    def load_json(self, name: str) -> dict[str, Any]:
        if name in self._json_cache:
            return dict(self._json_cache[name])

        path = self._json_path(name)
        if not path.exists():
            data: dict[str, Any] = {}
            self._json_cache[name] = data
            return dict(data)

        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)

        self._json_cache[name] = data
        return dict(data)

    def feature_ic_summary(self) -> pd.DataFrame:
        return self.load_csv("feature_ic_summary.csv")

    def alpha_model_performance(self) -> pd.DataFrame:
        return self.load_csv("alpha_model_performance.csv")

    def portfolio_performance(self) -> pd.DataFrame:
        return self.load_csv("portfolio_performance_comparison.csv")

    def weights_log(self) -> pd.DataFrame:
        df = self.load_csv("weights_log.csv")
        if df.empty:
            return df
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
        return df

    def final_model_registry(self) -> dict[str, Any]:
        return self.load_json("final_model_registry.json")

    def model_registry(self) -> dict[str, Any]:
        return self.load_json("model_registry.json")

    def fold_params(self) -> dict[str, Any]:
        return self.load_json("fold_params.json")

    def feature_meta(self) -> dict[str, Any]:
        return self.load_json("feature_meta.json")

    def regime_meta(self) -> dict[str, Any]:
        return self.load_json("regime_meta.json")

    def meta_model_meta(self) -> dict[str, Any]:
        return self.load_json("meta_model_meta.json")
