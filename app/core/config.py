from __future__ import annotations

from functools import lru_cache
import logging
from pathlib import Path
import shutil

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

    @property
    def app_root(self) -> Path:
        return Path(__file__).resolve().parents[2]

    @property
    def local_data_root(self) -> Path:
        return self.app_root / "data"

    def _ensure_local_copy(self, source: Path, destination: Path) -> None:
        if destination.exists():
            return
        destination.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            shutil.copytree(source, destination, dirs_exist_ok=True)
        else:
            shutil.copy2(source, destination)

    def _resolve_path(self, path: Path | None, fallback: Path) -> Path:
        if path is None:
            return fallback
        return path if path.is_absolute() else (self.repo_root / path)

    def _resolve_with_local_copy(
        self,
        path: Path | None,
        fallback_source: Path,
        local_target: Path,
    ) -> Path:
        logger = logging.getLogger(__name__)
        resolved = self._resolve_path(path, fallback_source)
        if resolved.exists():
            self._ensure_local_copy(resolved, local_target)
            return resolved
        if local_target.exists():
            logger.info("Falling back to local data copy at %s", local_target)
            return local_target
        if fallback_source.exists():
            self._ensure_local_copy(fallback_source, local_target)
            logger.info("Falling back to local data copy at %s", local_target)
            return local_target
        return resolved

    @property
    def resolved_sp500_data_dir(self) -> Path:
        fallback = self.repo_root / "BTP" / "sp500"
        local_target = self.local_data_root / "sp500"
        return self._resolve_with_local_copy(self.sp500_data_dir, fallback, local_target)

    @property
    def resolved_model_data_dir(self) -> Path:
        fallback = self.repo_root / "BTP" / "models_p3_metaquant"
        local_target = self.local_data_root / "models_p3_metaquant"
        return self._resolve_with_local_copy(self.model_data_dir, fallback, local_target)

    @property
    def resolved_ticker_mapping_file(self) -> Path:
        fallback = self.repo_root / "BTP" / "extra_data" / "ticker_to_company_mapping.csv"
        local_target = self.local_data_root / "extra_data" / "ticker_to_company_mapping.csv"
        return self._resolve_with_local_copy(self.ticker_mapping_file, fallback, local_target)

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.allow_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
