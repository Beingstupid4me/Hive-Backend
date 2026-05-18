# Hive Meta-Quant FastAPI Backend

Institutional-style backend for the terminal frontend metrics contract (`frontend/metrics.md`).

## What This Service Provides

- Modular FastAPI architecture (`api`, `services`, `providers`, `repositories`, `schemas`).
- Route groups aligned to the frontend contract:
  - `/api/system/status`
  - `/api/landing/overview`
  - `/api/macro/*`
  - `/api/alpha/*`
  - `/api/risk/*`
  - `/api/agent/*`
  - `/api/backtest/{run_id}`
  - `/api/execution/*`
  - `/api/optimizer/*`
  - `/api/metrics/snapshot`
- Dual data mode with `HISTORICAL_DATA` switch:
  - `true`: loads from local S&P 500 files in `BTP/sp500` and model artifacts in `BTP/models_p3_metaquant`.
  - `false`: loads live market data from free open APIs with fallback to historical files.

## Free APIs Used in Live Mode

- Yahoo Finance via `yfinance` (quotes + candles).
- CoinGecko public API (`/global`) for aggregate 24h volume.

## Environment Variables

Copy `.env.example` to `.env` and adjust values.

- `HISTORICAL_DATA=true|false` (also supports `Historical_Data`)
- `SP500_DATA_DIR` (optional)
- `MODEL_DATA_DIR` (optional)
- `TICKER_MAPPING_FILE` (optional)
- `ALLOW_ORIGINS`
- `MAX_UNIVERSE_SIZE`
- `BASE_NOTIONAL_USD`

## Run Locally

```bash
cd AI-backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open:

- Docs: `http://localhost:8000/docs`
- Health: `http://localhost:8000/api/health`
- Full snapshot: `http://localhost:8000/api/metrics/snapshot`

## Notes

- Historical mode is deterministic and uses your repository artifacts for model/risk/regime metrics.
- Optimizer results are stored in-memory per process (`/api/optimizer/solve` then `/api/optimizer/{job_id}`).
- Contact and execution order endpoints are mock-safe and do not require credentials.
