# FloodLens AI — AI-Based Urban Flood Hotspot Predictor

**Hackathon MVP · Chennai, Tamil Nadu, India.** A full-stack disaster-management
dashboard that estimates urban flood risk for Chennai localities, integrates a
live rainfall forecast, accepts community waterlogging reports, and trains *and
honestly evaluates* a baseline classifier on the supplied flood dataset.

> ⚠️ **This is a prototype, not an official flood-warning system.** Every risk
> number is a clearly-labelled **Demo Risk Estimate**. Do not use it for
> emergency decisions.

---

## What it does

| Area | Status |
|---|---|
| React + Vite + TypeScript dashboard | ✅ polished, responsive (dark navy sidebar, light dashboard) |
| Leaflet + OpenStreetMap map of Chennai | ✅ 12 localities with verified OSM coordinates |
| Transparent rule-based risk engine | ✅ deterministic, explainable, ~10 ms, "Demo Risk Estimate" |
| Open-Meteo live weather / rainfall | ✅ real source, units, UTC retrieval time, offline/demo state on failure |
| Community waterlogging reports | ✅ SQLite-backed, always marked *user-submitted*, no PII |
| scikit-learn baseline classifier | ✅ trained + evaluated + wired to the API (see "Honest verdict") |
| Tests | ✅ 61 backend tests + live smoke script + frontend typecheck/build |

---

## Honest verdict on the training dataset (read this first)

`data/flood_risk_dataset_india.csv` (10,000 rows × 14 columns) was verified at
runtime and in tests:

* No nulls, no duplicates, target 49.4 % / 50.6 %.
* **Every feature is statistically independent of the label.** Single-feature
  AUCs range 0.489–0.516 (0.5 = coin flip); all numeric columns are perfectly
  uniform distributions — the signature of a synthetic random generator.
* The trained logistic regression scores **test accuracy 0.4965, ROC-AUC 0.4985**
  against a majority baseline of **0.5055** and a shuffled-label control of
  **AUC 0.4845** — indistinguishable from noise.
* Elevation values are implausible for city-scale analysis (a coastal Chennai
  row lists 6,000+ m), and only 6 of 10,000 rows lie near Chennai.

**Therefore:** the trained model is kept as a **documented negative result**.
It is returned by `POST /api/assess` under `ml_prototype` with `reliable: false`
and shown in the dashboard's **Model information** panel with its real metrics.
The live Chennai risk numbers come from the transparent rule engine, so the app
never displays coin-flip output as a prediction. A future *real* labelled
dataset can be plugged in via `backend/app/prediction/` without touching the API
layer.

---

## Quick start (Windows PowerShell)

### 1 · Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m app.ml.train          # trains + evaluates the model, writes backend/models/*
python -m pytest -q             # run the test suite (61 tests)
python -m uvicorn app.main:app --reload --port 8000
```

API docs: <http://127.0.0.1:8000/docs>

### 2 · Frontend (second terminal)

```powershell
cd frontend
npm install
npm run dev                     # http://localhost:5173
```

CORS allows only `http://localhost:5173` and `http://127.0.0.1:5173`.

### 3 · Live smoke test (backend running)

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\smoke.ps1
```

---

## API endpoints

| Method | Path | Notes |
|---|---|---|
| GET | `/api/health` | status, predictor modes, DB health, weather config |
| GET | `/api/zones` | 12 Chennai zones + live-computed baseline Demo Risk Estimate |
| POST | `/api/assess` | rule estimate + ml prototype (reliable=false); validations → 404/422 |
| GET | `/api/weather?latitude=..&longitude=..` | Open-Meteo forecast; `available:false` on outage (never fabricated values) |
| GET | `/api/reports?limit=..&zone_id=..` | recent user-submitted reports |
| POST | `/api/reports` | create report; no PII fields accepted |
| GET | `/api/model` | real metrics, baselines, verdict, dataset integrity |

Rainfall resolution order in `/api/assess`: caller-supplied values → live
Open-Meteo forecast → documented illustrative defaults (only when the caller
explicitly opts in). Otherwise `422` with a helpful message. Weather-derived
inputs and illustrative terrain/drainage inputs are always reported in separate
buckets.

---

## Project layout

```
data/                     flood_risk_dataset_india.csv (synthetic, documented)
backend/
  app/
    main.py               FastAPI app, CORS, 422 error handler
    config.py             paths + settings (env-overridable)
    schemas.py            strict Pydantic request/response models
    routers/              health · zones · assess · weather · reports · model_info
    services/             zone_catalog · weather_client (Open-Meteo) · reports_store (SQLite)
    prediction/           base · factors · rule_based (the real engine) · ml_predictor · registry
    ml/                   dataset · evaluate · train
  models/                 flood_model.joblib · model_metadata.json · model_metrics.json
  var/                    reports.sqlite3 (local)
  tests/                  61 tests (pytest)
frontend/
  src/
    api/                  client + types
    components/           dashboard sections
    hooks/useApi.ts       data hook (loading/error/reload)
    lib/format.ts         risk colours, formatting
scripts/smoke.ps1         live endpoint smoke test
```

---

## Data sources & limitations

* **Zones:** coordinates from OpenStreetMap place data (Nominatim), verified to
  lie inside the Chennai bounding box. All other zone attributes are
  **illustrative design assumptions**; mapped points are not verified flood
  hotspots.
* **Weather:** [Open-Meteo](https://open-meteo.com) free forecast API (CC BY
  4.0). Milliseconds/units/retrieval time surfaced in the UI. On outage the UI
  shows a visible offline/demo state; nothing is substituted silently.
* **Model:** trained on `data/flood_risk_dataset_india.csv`, which is synthetic
  and carries no measurable signal. Metrics describe that dataset only.
* **Reports:** unverified community submissions stored locally; not official
  records.
* **Not connected** to any official warning network; not suitable for
  operational decisions.

## Future improvements

1. Substitute a real labelled flood dataset (per-locality rainfall, elevation,
   observed flooding) — drop it into `data/`, update
   `backend/app/ml/dataset.py`, retrain, and point `prediction/registry.py` at
   the signal-bearing model.
2. Swap SQLite for PostGIS to cluster reports and intersect with ward polygons.
3. Read live rainfall from installed gauges / CWC stage data instead of model
   forecast.
4. Add zone ward-boundary polygons (OSM relation data) to replace centroids.
5. Auth-sensitive moderation API for reports and an export endpoint.