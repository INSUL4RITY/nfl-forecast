# NFL Forecasting Portfolio (`nflcast`)

A reproducible pipeline that forecasts expected scores, margin and total (and, later, outcome
probabilities) for every NFL regular-season and playoff game. Numbers come from code run on
real data. Nothing is hand-authored. The only market inputs are the point spread and the total.
Moneylines, prices and betting returns are excluded by design and enforced in code.

**Live site: https://insul4rity.github.io/nfl-forecast/** · Status and results are in [PROGRESS.md](PROGRESS.md).

## Setup (Windows, PowerShell)

```powershell
winget install Python.Python.3.12 --scope user        # if Python is not installed
& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

## Commands

```powershell
.\.venv\Scripts\python.exe -m nflcast audit      # Milestone 1 data availability audit -> reports/audit/
.\.venv\Scripts\python.exe -m nflcast ingest     # download/refresh raw snapshots (append-only) -> data/raw/
.\.venv\Scripts\python.exe -m nflcast build      # games, team-games, as-of features, market -> data/processed/
.\.venv\Scripts\python.exe -m nflcast backtest   # walk-forward evaluation (tune 2019-21, dev 2022-24) -> reports/backtest/
.\.venv\Scripts\python.exe -m nflcast tune       # window-setting grid on tune seasons only -> reports/tuning/
.\.venv\Scripts\python.exe -m nflcast predict    # immutable release for the next week -> releases/
.\.venv\Scripts\python.exe -m nflcast score      # score frozen live releases -> reports/prospective/
.\.venv\Scripts\python.exe -m nflcast export-web # versioned JSON -> web/public/data/
.\.venv\Scripts\python.exe -m nflcast operate    # scheduled cycle (see docs/operations.md)
.\.venv\Scripts\python.exe -m nflcast all        # ingest + build + backtest + predict
.\.venv\Scripts\python.exe -m pytest -q          # leakage, sign, identity, probability, scoring, policy tests
# (locked-test is a one-time command and has already been used for 2025)
```

Website (Node.js 24):

```powershell
cd web; npm install; npx next build   # static site in web/out/
```

## Layout

| Path | Responsibility |
|---|---|
| `src/nflcast/data/` | source adapters, append-only snapshots, market policy, games/market tables, audit |
| `src/nflcast/features/` | play-by-play aggregation, as-of team features and ratings |
| `src/nflcast/models/` | market benchmarks, naive floor, football-only ridge |
| `src/nflcast/evaluation/` | walk-forward backtest, metrics, block bootstrap |
| `src/nflcast/pipeline.py` | ingest / build / backtest steps with run manifests |
| `src/nflcast/predict/` | releases, scoring, website export, scheduled operation |
| `configs/production.yaml` | frozen production model choices |
| `web/` | Next.js + TypeScript static site (renders exported JSON only) |
| `configs/settings.yaml` | seasons, horizons, feature settings, validation folds |
| `tests/` | leakage, sign convention, identities, market policy (synthetic CI fixture) |
| `docs/` | data sources and availability, methodology |
| `reports/` | generated audit and backtest reports |
| `releases/` | immutable forecast releases (JSON) |
| `data/` | local raw/processed data (ignored by git; re-creatable with `ingest` + `build`) |

## Data attribution
Data: nflverse (CC-BY-4.0). FTN charting: "FTN Data via nflverse" (CC-BY-SA 4.0), if/when used.
Snap counts and advanced stats originate from Pro-Football-Reference. See [docs/data_sources.md](docs/data_sources.md).

This project is inspired by the presentation of davidsasser.com/nfl. It does not reconstruct or claim
to know that site's model.
