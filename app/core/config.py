from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Hive Meta-Quant Engine API"
    app_version: str = "0.1.0"
    app_env: str = "dev"
    host: str = "0.0.0.0"
    port: int = 8000

    historical_data: bool = Field(
        default=True,
        validation_alias=AliasChoices("HISTORICAL_DATA", "Historical_Data"),
    )

    sp500_data_dir: Path | None = Field(default=None, alias="SP500_DATA_DIR")
    model_data_dir: Path | None = Field(default=None, alias="MODEL_DATA_DIR")
    ticker_mapping_file: Path | None = Field(default=None, alias="TICKER_MAPPING_FILE")

    coingecko_base_url: str = "https://api.coingecko.com/api/v3"
    yahoo_timeout_sec: int = 10

    default_user_initials: str = "QR"
    allow_origins: str = "http://localhost:3000,http://localhost:3001"

    max_universe_size: int = 150
    random_seed: int = 42
    base_notional_usd: float = 420_000_000.0

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        protected_namespaces=("settings_",),
    )

    @property
    def repo_root(self) -> Path:
        return Path(__file__).resolve().parents[3]

    def _resolve_path(self, path: Path | None, fallback: Path) -> Path:
        if path is None:
            return fallback
        return path if path.is_absolute() else (self.repo_root / path)

    @property
    def resolved_sp500_data_dir(self) -> Path:
        return self._resolve_path(self.sp500_data_dir, self.repo_root / "BTP" / "sp500")

    @property
    def resolved_model_data_dir(self) -> Path:
        return self._resolve_path(
            self.model_data_dir,
            self.repo_root / "BTP" / "models_p3_metaquant",
        )

    @property
    def resolved_ticker_mapping_file(self) -> Path:
        return self._resolve_path(
            self.ticker_mapping_file,
            self.repo_root / "BTP" / "extra_data" / "ticker_to_company_mapping.csv",
        )

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.allow_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
