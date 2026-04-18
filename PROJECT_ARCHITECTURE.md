# AirRoute — Complete Project Architecture & Technical Reference

> **Purpose**: This document is designed to be detailed enough to create a coherent PowerPoint presentation from.  
> It covers every folder, every file, every import, every ML model, and every mathematical formula used across the entire AirRoute system.

---

## 1. Project Overview (Slide 1)

**AirRoute** is a **pollution-aware smart navigation system** that calculates two routes for every trip:
- 🔵 **Fastest Route** — Shortest travel time (like Google Maps)
- 🟢 **Cleanest Route** — Lowest air pollution exposure

It then evaluates whether the cleaner route is **"worth the detour"** by translating the exposure difference into an equivalent number of cigarettes of smog inhaled.

**Key Innovation**: The system doesn't just compare AQI numbers — it models **physiological PM2.5 inhalation** based on your transport mode (walking inhales 3× more pollutants than driving due to higher breathing rate).

---

## 2. Full Folder Structure (Slide 2)

```
filter-rout/
│
├── src/                          # ← All backend source code
│   ├── main.py                   # FastAPI application entry point
│   ├── api/
│   │   └── aqi_service.py        # Multi-source AQI data fetcher (4 APIs)
│   ├── sensors/
│   │   └── aqi_sensor.py         # Hardware/mock air quality sensor
│   ├── fusion/
│   │   └── fusion_engine.py      # Blends sensor + API data with weights
│   ├── routing/
│   │   ├── basic_router.py       # Dual-path routing engine (OSMnx/NetworkX)
│   │   └── evaluator.py          # "Worth-It" cigarette equivalence evaluator
│   ├── prediction/
│   │   ├── predictor.py          # AQI forecasting (Gradient Boosting)
│   │   ├── data_loader.py        # Weather & lag feature engineering
│   │   ├── spatial_interpolator.py # Street-level AQI estimation (KDTree + RF)
│   │   └── ventilation.py        # Physiological PM2.5 inhalation model
│   ├── data/
│   │   ├── logger.py             # SQLite database logger for history
│   │   └── download_graph.py     # OSM street graph downloader
│   └── demo/                     # ← NEW: Demo mode edge-case simulator
│       ├── config.py
│       ├── mock_data.py
│       ├── scenarios.py
│       ├── middleware.py
│       └── demo_logger.py
│
├── static/                       # ← Frontend web application
│   ├── index.html                # Dashboard HTML structure
│   ├── style.css                 # Glassmorphic dark theme styling
│   └── app.js                    # Map interaction + API bridge logic
│
├── scripts/                      # ← Utility/test/data scripts
│   ├── backfill_data.py          # Downloads 2 years of historical AQI
│   ├── fetch_history.py          # Downloads 90 days of AQI history
│   ├── simulate_phase2.py        # End-to-end pipeline simulation
│   ├── verify_phase3.py          # Multi-mode verification test
│   ├── test_route.py             # Single route calculation test
│   └── test_resilience.py        # API failure chaos testing
│
├── data/                         # ← Generated data files (not in git)
│   ├── air_quality_history.db    # SQLite database (~1.5 MB)
│   ├── aqi_cache.json            # Last-known AQI fallback cache
│   ├── bengaluru_drive.graphml   # Bengaluru driving road network (~150 MB)
│   ├── bengaluru_bike.graphml    # Bengaluru cycling network (~165 MB)
│   ├── bengaluru_walk.graphml    # Bengaluru walking network (~183 MB)
│   ├── amsterdam_drive.graphml   # Amsterdam driving road network (~16 MB)
│   ├── amsterdam_bike.graphml    # Amsterdam cycling network (~38 MB)
│   └── amsterdam_walk.graphml    # Amsterdam walking network (~62 MB)
│
├── requirements.txt              # Python dependencies
├── PROJECT_STATUS.md             # Project completion tracker
├── AirRoute_SOP.md               # Standard Operating Procedure
├── BEGINNER_GUIDE.md             # Setup instructions
└── TESTING_GUIDE.md              # Testing documentation
```

---

## 3. Backend Entry Point: `src/main.py` (Slide 3)

### Role
The **central orchestrator** — initializes all system components and exposes the REST API.

### Imports Used
| Import | Package | Purpose |
|--------|---------|---------|
| `FastAPI` | `fastapi` | ASGI web framework for building the REST API |
| `Query` | `fastapi` | Query parameter validation with enum constraints |
| `HTTPException` | `fastapi` | Structured error responses (500, 400, etc.) |
| `StaticFiles` | `fastapi.staticfiles` | Serves the frontend HTML/CSS/JS from `/static` |
| `FileResponse` | `fastapi.responses` | Returns `index.html` at the root `/` URL |
| `BaseModel` | `pydantic` | Response schema validation (`RouteResponse`) |
| `asynccontextmanager` | `contextlib` | Manages startup/shutdown lifecycle hooks |
| `threading.Lock` | `threading` | Thread-safe lazy loading of city graph data |
| `asyncio.to_thread` | `asyncio` | Offloads blocking routing computation to thread pool |

### API Endpoints
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `GET /` | GET | Serves the frontend dashboard (`static/index.html`) |
| `GET /route` | GET | Calculates fastest + cleanest routes between two coordinates |
| `GET /stats` | GET | Returns current AQI + forecast without routing overhead |
| `GET /health` | GET | System health check (loading status, mode) |

### Request Flow for `/route`
```
User clicks map → Frontend sends GET /route?start_lat=...&end_lat=...&mode=car&city=bengaluru
       ↓
1. aqi_manager.fetch_all_safe()        → Calls 4 AQI APIs simultaneously
2. sensor.read_aqi()                   → Reads local air sensor value
3. fusion_engine.fuse(sensor, api)     → Blends both into one AQI number
4. logger.log_reading(city, ...)       → Stores reading in SQLite history
5. router.get_dual_routes(start, end)  → Computes fastest + cleanest paths
6. evaluator.evaluate(fastest, clean)  → Decides if detour is worth it
7. predictor.predict(city, aqi, hours) → Forecasts AQI at +1h, +3h, +7d
       ↓
Returns JSON: { route_fastest, route_quality, worth_it, worth_it_reason, forecasts }
```

---

## 4. AQI Data Layer: `src/api/aqi_service.py` (Slide 4)

### Role
Connects to **4 real-world air quality APIs**, normalizes their data into a common format, and implements graceful degradation (if some APIs fail, the system keeps working).

### Imports Used
| Import | Purpose |
|--------|---------|
| `requests` | HTTP client for calling external APIs |
| `time`, `os`, `json` | Caching, file I/O |
| `datetime`, `timedelta` | Timestamp handling |

### The 4 API Clients

| Class | API | URL | Data Returned |
|-------|-----|-----|---------------|
| `LuchtmeetnetClient` | Dutch National Air Quality | `api.luchtmeetnet.nl/open_api` | Multi-station PM2.5/PM10/NO2 readings across Netherlands |
| `OpenAQv3Client` | OpenAQ v3 (Global) | `api.openaq.org/v3` | Location-based measurements with lat/lon coordinates |
| `WAQIClient` | World AQI Index | `api.waqi.info/feed/{city}` | Single composite AQI value per city |
| `IQAirClient` | IQAir / AirVisual | `api.airvisual.com/v2` | US AQI with dominant pollutant identification |

### Normalized Data Schema
Every API client returns data in this common format:
```python
{
    "station": "Station Name",        # Monitoring station identifier
    "value": 42.0,                    # AQI value (numeric)
    "formula": "pm25",                # Dominant pollutant (PM2.5, NO2, etc.)
    "timestamp": "2026-04-15T09:00Z", # ISO timestamp
    "lat": 12.9716,                   # Latitude
    "lon": 77.5946                    # Longitude
}
```

### `AQIManager` — The Aggregator
Manages all 4 clients and implements **graceful degradation**:

| Status | Meaning | When |
|--------|---------|------|
| `API_FULL` | All APIs responded successfully | 0 APIs down |
| `DEGRADED` | Some APIs failed, others worked | 1-3 APIs down |
| `CACHE_ONLY` | All APIs failed, using cached value | 4 APIs down |

**Fallback Logic**: Last known good AQI is cached to `data/aqi_cache.json`. If all APIs fail, the system serves cached data instead of crashing.

---

## 5. Sensor Layer: `src/sensors/aqi_sensor.py` (Slide 5)

### Role
Simulates a **hardware air quality sensor** (MQ-135 / SDS011) for development. In production, this would be replaced with PySerial readings from a physical sensor connected via UART.

### Imports Used
| Import | Purpose |
|--------|---------|
| `random` | Generates realistic sensor noise/fluctuation |
| `time` | Used in standalone testing loop |

### How It Works
```python
class MockAQISensor:
    def __init__(self, base_val=45, noise=5):  # Base AQI = 45, ±5 variation
    
    def read_aqi(self) -> float:
        fluctuation = random.uniform(-self.noise, self.noise)  # -5 to +5
        return max(0, self.base_val + fluctuation)             # Clamp ≥ 0
```

**Output**: Returns a value between 40–50 AQI on each call, simulating real-world sensor jitter.

---

## 6. Fusion Engine: `src/fusion/fusion_engine.py` (Slide 6)

### Role
**Blends** the local sensor reading with the API average using **weighted averaging** to produce a single trusted AQI value.

### The Fusion Formula

```
Fused_AQI = (W_sensor × Sensor_Value) + (W_api × API_Value)
```

**Default Weights**:
| Source | Weight | Rationale |
|--------|--------|-----------|
| Local Sensor (`W_sensor`) | **0.6 (60%)** | Hyperlocal, real-time, more relevant to user's actual location |
| API Average (`W_api`) | **0.4 (40%)** | Broad coverage, validated data, but less location-specific |

### Fallback Chain
| Scenario | Result |
|----------|--------|
| Both available | `0.6 × sensor + 0.4 × api` |
| Sensor only | `sensor_val` (100%) |
| API only | `api_val` (100%) |
| Neither available | `50.0` (safe default) |

---

## 7. Routing Engine: `src/routing/basic_router.py` (Slide 7-8)

### Role
The **core navigation engine**. Loads OpenStreetMap road networks and computes two paths: one optimized for speed, one optimized for air quality.

### Imports Used
| Import | Package | Purpose |
|--------|---------|---------|
| `osmnx (ox)` | `osmnx` | Loads `.graphml` road network files with node/edge attributes |
| `networkx (nx)` | `networkx` | Graph algorithms: Dijkstra's shortest path |
| `numpy (np)` | `numpy` | Vectorized array operations for batch AQI projection |
| `MinuteVentilationModel` | `src.prediction.ventilation` | Physiological breathing model |
| `SpatialInterpolator` | `src.prediction.spatial_interpolator` | Street-level AQI estimation |

### Road Network Data
The system uses **pre-downloaded OpenStreetMap graphs** stored as `.graphml` files:

| File | Size | Contents |
|------|------|----------|
| `bengaluru_drive.graphml` | ~150 MB | All roads accessible by cars (nodes: intersections, edges: road segments) |
| `bengaluru_bike.graphml` | ~165 MB | All roads/paths accessible by bicycle |
| `bengaluru_walk.graphml` | ~183 MB | All roads/paths/sidewalks accessible on foot |

### Mode-Specific AQI Sensitivity
Different transport modes expose users to different pollution levels due to breathing rate:

| Mode | Sensitivity Multiplier | Reason |
|------|----------------------|--------|
| Car | **1.0×** | Sealed cabin, AC filtration, low breathing rate |
| Bike | **1.5×** | Open air, moderate exertion → higher breathing |
| Walk | **2.0×** | Open air, street-level exposure, exercise breathing |

### The AQI Penalty Formula (Applied to Every Road Edge)

```
AQI_Penalty = Travel_Time × (1 + (Edge_AQI × Sensitivity / 100))
```

**Example**: A road segment taking 60 seconds with AQI = 80, for a cyclist:
```
Penalty = 60 × (1 + (80 × 1.5 / 100)) = 60 × 2.2 = 132
```
The "cleanest" route minimizes the **sum of penalties** across all edges.

### Dual Routing Algorithm
```
1. Load city graph for selected mode (drive/bike/walk)
2. Project AQI onto every edge using SpatialInterpolator
3. Calculate AQI_Penalty for every edge
4. Route A: Dijkstra's shortest path using weight = "travel_time"      → Fastest
5. Route B: Dijkstra's shortest path using weight = "aqi_penalty"      → Cleanest
6. Return both routes with metrics
```

### Haversine Distance Formula (Fallback)
When the graph doesn't cover the requested area, a straight-line fallback uses the **Haversine formula** to calculate distance between two GPS coordinates on a sphere:

```
a = sin²(Δφ/2) + cos(φ₁) × cos(φ₂) × sin²(Δλ/2)

Distance_km = 2 × R × atan2(√a, √(1−a))

where:
  R = 6371 km (Earth's radius)
  φ = latitude in radians
  λ = longitude in radians
```

---

## 8. Worth-It Evaluator: `src/routing/evaluator.py` (Slide 9)

### Role
Decides whether the cleaner route is worth the extra travel time by quantifying PM2.5 savings in terms of **cigarette equivalents**.

### The Cigarette Equivalence Model

```
1 cigarette ≈ 22 µg of PM2.5 inhaled

Cigarettes_Saved = (PM2.5_fastest - PM2.5_cleanest) / 22.0
```

### Decision Logic
| Condition | Result |
|-----------|--------|
| PM2.5 saving ≥ 2.0 µg AND extra time ≤ 10 min | ✅ **Worth it** — "Saves X cigarettes of smog" |
| PM2.5 saving < 2.0 µg | ❌ **Not worth it** — "Air quality improvement is negligible" |
| Extra time > 10 min | ❌ **Not worth it** — "Time penalty too high" |

### Example Output
```
"Taking this route saves you from inhaling the equivalent of 1.6 cigarettes worth of smog."
```

---

## 9. Prediction Engine: `src/prediction/predictor.py` (Slide 10)

### Role
Forecasts future AQI values at **+1 hour**, **+3 hours**, and **+7 days** using machine learning.

### Imports Used
| Import | Package | Purpose |
|--------|---------|---------|
| `GradientBoostingRegressor` | `sklearn.ensemble` | The ML model for AQI forecasting |
| `mean_absolute_error` | `sklearn.metrics` | Model evaluation metric |
| `pandas (pd)` | `pandas` | DataFrame operations for time-series data |
| `numpy (np)` | `numpy` | Array operations |
| `PredictionDataLoader` | `src.prediction.data_loader` | Feature engineering + weather data |

### ML Model: Gradient Boosting Regressor

| Parameter | Value | Purpose |
|-----------|-------|---------|
| Algorithm | `GradientBoostingRegressor` | Ensemble of decision trees, each correcting predecessor's errors |
| `n_estimators` | 150 | Number of sequential boosting trees |
| `learning_rate` | 0.1 | Step size at each iteration (controls overfitting) |
| `random_state` | 42 | Reproducibility seed |

### Feature Set (7 input features)
| Feature | Source | Description |
|---------|--------|-------------|
| `hour` | Derived from timestamp | Hour of day (0–23) — captures rush hour patterns |
| `dayofweek` | Derived from timestamp | Day of week (0=Mon, 6=Sun) — captures weekday vs weekend |
| `lag_1h` | Historical data | AQI value 1 hour ago (autoregressive signal) |
| `lag_3h` | Historical data | AQI value 3 hours ago (trend signal) |
| `wind_speed` | Open-Meteo API | Current wind speed in km/h (disperses pollutants) |
| `temperature` | Open-Meteo API | Current temperature °C (affects atmospheric stability) |
| `traffic_index` | Synthetic estimate | Rush hour congestion (0.2 off-peak, 0.8–0.9 peak) |

### Prediction Dampening Formula
For long horizons (e.g., 7 days), the model blends current AQI with the ML prediction:

```
weight = max(0.0, 1.0 − (horizon_hours / 24.0))

Final_AQI = (weight × Current_AQI) + ((1 − weight) × ML_Prediction)
```

**Effect**: At +1h, current AQI contributes ~96%. At +24h, it's 0% (pure model). At +168h (7d), fully model-driven.

### Training Data
- **Source**: `data/air_quality_history.db` (SQLite)
- **Volume**: ~17,500 hourly records per city (2 years backfilled via Open-Meteo API)
- **Split**: 80% train / 20% test
- **Metric**: Mean Absolute Error (MAE) in AQI units

---

## 10. Spatial Interpolator: `src/prediction/spatial_interpolator.py` (Slide 11)

### Role
Estimates **street-level AQI** for every road segment in the graph, even between official sensor stations. This is what makes the "cleanest route" work — without this, every road would have the same AQI.

### Imports Used
| Import | Package | Purpose |
|--------|---------|---------|
| `RandomForestRegressor` | `sklearn.ensemble` | ML model for spatial AQI prediction |
| `KDTree` | `sklearn.neighbors` | Efficient nearest-neighbor lookup for sensor proximity |
| `numpy (np)` | `numpy` | Vectorized batch operations |

### ML Model: Random Forest Regressor

| Parameter | Value | Purpose |
|-----------|-------|---------|
| Algorithm | `RandomForestRegressor` | Ensemble of independent decision trees (handles non-linear patterns) |
| `n_estimators` | 50 | Number of trees in the forest |
| `random_state` | 42 | Reproducibility |

### How It Works: KDTree + Random Forest Pipeline

```
Step 1: Build KDTree from official sensor station coordinates
        → KDTree enables O(log n) nearest-neighbor lookup

Step 2: Train Random Forest on synthetic training data:
        Features: [distance_to_nearest_sensor, base_sensor_value, is_motorway]
        Label:    estimated_AQI

Step 3: For each road edge in the graph:
        a) Query KDTree → find nearest sensor + distance (degrees × 111,000 ≈ meters)
        b) Check highway type (motorway/trunk/primary = high pollution)
        c) Predict AQI using Random Forest

Step 4: Clip prediction to valid range [0, 500]
```

### The Spatial Degradation Logic
```
drift = (50.0 − base_sensor_value) × (distance / 5000.0)
motorway_penalty = random(20, 50) if is_motorway else random(0, 5)
estimated_AQI = base_sensor_value + drift + motorway_penalty
```

**Meaning**: Farther from sensors → AQI drifts toward baseline (50). Motorways/highways → automatic pollution penalty (+20 to +50).

### Batch Prediction (Performance Optimization)
Instead of predicting AQI for each edge individually, the system:
1. Collects ALL edge coordinates into a NumPy array
2. Runs a **single bulk KDTree query** for all edges
3. Runs a **single batch `model.predict()`** call
4. Applies results back — **O(1) model calls instead of O(n)**

---

## 11. Ventilation Model: `src/prediction/ventilation.py` (Slide 12)

### Role
Models how much PM2.5 a person **physically inhales** based on their transport mode, speed, and incline. This is the physiological bridge between AQI and actual health impact.

### Imports Used
| Import | Package | Purpose |
|--------|---------|---------|
| `RandomForestRegressor` | `sklearn.ensemble` | Predicts Minute Ventilation (V_E) |
| `StandardScaler` | `sklearn.preprocessing` | Normalizes input features |
| `numpy (np)` | `numpy` | Synthetic data generation |

### ML Model: Random Forest for Minute Ventilation (V_E)

| Parameter | Value |
|-----------|-------|
| Algorithm | `RandomForestRegressor` |
| `n_estimators` | 50 |
| Training | Self-trained on 2,000 synthetic physiological samples |

### What is Minute Ventilation (V_E)?
V_E = **Volume of air breathed per minute** (Liters/min). Higher V_E = more pollutants inhaled.

| Activity | Typical V_E (L/min) |
|----------|---------------------|
| Sitting in car | 6–8 |
| Walking (5 km/h) | 12–18 |
| Cycling (20 km/h) | 20–35 |
| Cycling uphill (20 km/h, 10% grade) | 40–55 |

### Synthetic Training Data Logic
```python
# Car (sedentary): V_E ≈ 7.0 ± 1.0 L/min (regardless of speed)
# Bike: V_E ≈ 20 + (speed - 15) × 1.5 + max(0, incline) × 3.0
# Walk: V_E ≈ 12 + (speed - 4) × 2.5 + max(0, incline) × 1.5
```

### PM2.5 Inhalation Formula

**Step 1**: Convert AQI to PM2.5 concentration (µg/m³)
```
If AQI ≤ 50:    PM2.5 = (12.0 / 50.0) × AQI
If AQI ≤ 100:   PM2.5 = ((35.4 − 12.1) / 50) × (AQI − 50) + 12.1
If AQI > 100:   PM2.5 = ((55.4 − 35.5) / 50) × (AQI − 100) + 35.5
```

**Step 2**: Convert concentration to inhaled micrograms
```
Concentration_µg/L = PM2.5_µg/m³ / 1000

Total_Inhaled_µg = Concentration_µg/L × V_E (L/min) × Duration (min)
```

**Example**: Walking 20 min in AQI 80 area:
```
PM2.5 = ((35.4 − 12.1)/50) × (80 − 50) + 12.1 = 26.08 µg/m³
V_E = ~15 L/min (walking)
Inhaled = (26.08/1000) × 15 × 20 = 7.82 µg
Cigarette equivalent = 7.82 / 22 ≈ 0.36 cigarettes
```

---

## 12. Data Layer: `src/data/` (Slide 13)

### `logger.py` — SQLite Persistence

| Import | Purpose |
|--------|---------|
| `sqlite3` | Embedded database (no server needed) |
| `os` | Ensures `data/` directory exists |
| `datetime` | Timestamps |

**Database Schema** (`measurements` table):
| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PK | Auto-incrementing row ID |
| `timestamp` | DATETIME | When the reading was taken |
| `city` | TEXT | `bengaluru` or `amsterdam` |
| `fused_aqi` | REAL | Blended AQI (output of fusion engine) |
| `api_aqi` | REAL | API average at that time |
| `sensor_aqi` | REAL | Local sensor reading at that time |

**Maintenance**: Records older than 90 days are auto-pruned on server startup.

### `download_graph.py` — Road Network Downloader

| Import | Purpose |
|--------|---------|
| `osmnx (ox)` | Downloads OpenStreetMap graph data for a city |
| `argparse` | CLI argument parsing (city name, modes) |

Downloads 3 graph files per city (drive, bike, walk) from OpenStreetMap using the OSMnx library.

---

## 13. Weather Data: `src/prediction/data_loader.py` (Slide 14)

### Role
Fetches real-time weather data and engineers time-series features for the prediction model.

### Imports Used
| Import | Package | Purpose |
|--------|---------|---------|
| `requests` | `requests` | Calls Open-Meteo weather API |
| `pandas (pd)` | `pandas` | DataFrame manipulation |
| `numpy (np)` | `numpy` | Random synthetic data for missing weather history |

### Weather Source: Open-Meteo API (Free, No Key)
```
URL: https://api.open-meteo.com/v1/forecast
     ?latitude={lat}&longitude={lon}&current_weather=true
```
Returns: temperature, wind speed, wind direction.

### City Coordinates
| City | Latitude | Longitude |
|------|----------|-----------|
| Bengaluru | 12.9716 | 77.5946 |
| Amsterdam | 52.3676 | 4.9041 |

### Feature Engineering for ML
The `engineer_lag_features()` method creates:
- `lag_1h` = AQI shifted by 1 row (1 hour ago)
- `lag_3h` = AQI shifted by 3 rows (3 hours ago)
- `wind_speed` = Synthetic ∈ [5, 25] if missing
- `temperature` = Synthetic ∈ [5, 25] if missing
- `traffic_index` = 0.8–0.9 during rush hours (7–9am, 4–7pm), 0.2 otherwise

---

## 14. Frontend: `static/` (Slide 15-16)

### Technology Stack
| Technology | Version | Purpose |
|------------|---------|---------|
| HTML5 | — | Semantic page structure |
| CSS3 (Vanilla) | — | Glassmorphic dark theme, CSS Grid, Flexbox |
| JavaScript (Vanilla) | ES6+ | Map interaction, API calls, DOM updates |
| Leaflet.js | 1.9.4 | Interactive map with tile layers |
| CartoDB Dark Tiles | — | Dark-themed map visuals |
| Google Fonts (Outfit, Inter) | — | Modern typography |
| Font Awesome | 6.4.0 | UI icons |

### `index.html` — Dashboard Structure
- **Sidebar** (left panel):
  - Logo + City selector dropdown (Bengaluru / Amsterdam)
  - Transportation mode buttons (🚗 Car, 🚲 Bike, 🚶 Walk)
  - Start/End point inputs (populated by map clicks)
  - "Calculate Best Route" button
  - Results panel (fastest vs cleanest metrics, recommendation box)
  - Live AQI status (current index, +1h/+3h/+7d forecasts)
- **Map** (right panel):
  - Interactive Leaflet.js map with dark tiles
  - Markers for start (blue) and end (red) points
  - Polyline overlays for fastest (blue) and cleanest (green) routes
  - Legend overlay

### `style.css` — Design System
| CSS Variable | Value | Usage |
|-------------|-------|-------|
| `--bg-dark` | `#0a0c10` | Page background |
| `--sidebar-bg` | `rgba(18, 22, 30, 0.85)` | Glassy sidebar |
| `--accent-blue` | `#3b82f6` | Fastest route, primary actions |
| `--accent-green` | `#10b981` | Cleanest route, positive indicators |
| `--accent-red` | `#ef4444` | Destination marker |
| `--glass-border` | `rgba(255, 255, 255, 0.08)` | Glassmorphism borders |

**Glassmorphism** is achieved via `backdrop-filter: blur(12px)` on the sidebar.

### `app.js` — Frontend Logic
| Function | Purpose |
|----------|---------|
| `updateCityStats()` | Polls `GET /stats` every 15 seconds for live AQI |
| `calculateRoute()` | Calls `GET /route` with marker coordinates & mode |
| `renderRoutes(data)` | Draws polylines on map (blue=fast, green=clean) |
| `updatePanel(data)` | Updates sidebar with time/AQI/recommendation values |
| `showLoading()` / `hideLoading()` | Loading overlay during graph init or routing |

---

## 15. Scripts: `scripts/` (Slide 17)

| Script | Purpose | When to Run |
|--------|---------|-------------|
| `backfill_data.py` | Downloads **2 years** (730 days) of hourly AQI history from Open-Meteo for both cities. Stores 17,500+ records per city in SQLite. | Once, before training ML models |
| `fetch_history.py` | Downloads **90 days** of AQI history (lighter version of backfill). | Alternative to backfill for quick setup |
| `simulate_phase2.py` | Runs full pipeline end-to-end: API → Sensor → Fusion → Routing → Evaluation. Prints JSON snapshot. | Testing / demo |
| `verify_phase3.py` | Tests all 3 transport modes (car, bike, walk) with routing + prediction for Amsterdam. | Verification after code changes |
| `test_route.py` | Minimal test: calculates a single route from Dam Square to Rijksmuseum. | Quick sanity check |
| `test_resilience.py` | **Chaos testing**: Uses `unittest.mock.patch` to simulate API failures and verifies graceful degradation. Tests partial outage, total outage, sensor failure, and total blackout. | Resilience verification |

---

## 16. External Dependencies: `requirements.txt` (Slide 18)

| Package | Version | Used For |
|---------|---------|----------|
| `osmnx` | ≥2.0.0 | Download & load OpenStreetMap road networks |
| `networkx` | ≥3.0 | Graph algorithms (Dijkstra's shortest path) |
| `pandas` | ≥2.0.0 | DataFrame operations for time-series ML |
| `requests` | ≥2.30.0 | HTTP client for external API calls |
| `fastapi` | ≥0.100.0 | REST API web framework |
| `uvicorn` | ≥0.23.0 | ASGI server to run FastAPI |
| `pydantic` | ≥2.0.0 | Request/response data validation |
| `matplotlib` | ≥3.7.0 | Plotting (used in analysis scripts) |
| `scipy` | ≥1.10.0 | Scientific computing utilities |
| `scikit-learn` | ≥1.3.0 | ML models (GradientBoosting, RandomForest, KDTree) |

---

## 17. Complete Data Flow Diagram (Slide 19)

```
┌─────────────────────────────────────────────────────────────────┐
│                      USER (Browser)                             │
│   Click map → Set start/end points → Choose mode → Calculate   │
└────────────────────────────┬────────────────────────────────────┘
                             │ GET /route?start_lat=...&mode=car
                             ▼
┌────────────────────────────────────────────────────────────────┐
│                   FastAPI Server (main.py)                      │
│                                                                │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────────┐   │
│  │  AQI Manager │   │ Mock Sensor  │   │  Fusion Engine   │   │
│  │  4× API calls│──▶│  read_aqi()  │──▶│  0.6×S + 0.4×A  │   │
│  │  (parallel)  │   │  base±noise  │   │  → Fused AQI     │   │
│  └──────┬───────┘   └──────────────┘   └────────┬─────────┘   │
│         │                                        │             │
│         │ raw sensor locations (lat/lon/value)   │ fused value │
│         ▼                                        ▼             │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              AirRouter (basic_router.py)                  │  │
│  │                                                          │  │
│  │  1. Load .graphml for city + mode                        │  │
│  │  2. SpatialInterpolator: KDTree + RandomForest           │  │
│  │     → Project AQI onto every road edge                   │  │
│  │  3. AQI_Penalty = time × (1 + aqi×sensitivity/100)      │  │
│  │  4. Dijkstra(weight="travel_time")   → Fastest Route     │  │
│  │  5. Dijkstra(weight="aqi_penalty")   → Cleanest Route    │  │
│  │  6. VentilationModel: V_E → PM2.5 inhaled (µg)          │  │
│  └──────────────────────────┬───────────────────────────────┘  │
│                             │                                  │
│                             ▼                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ WorthItEvaluator          │  AQIPredictor                │  │
│  │ PM2.5_saved / 22 = cigs   │  GradientBoosting            │  │
│  │ time_penalty vs threshold  │  +1h, +3h, +7d forecasts    │  │
│  └──────────────────────────────────────────────────────────┘  │
│                             │                                  │
│                             ▼                                  │
│              JSON Response to Browser                          │
└────────────────────────────────────────────────────────────────┘
```

---

## 18. ML Models Summary (Slide 20)

| Model | Algorithm | Location | Purpose | Features |
|-------|-----------|----------|---------|----------|
| **AQI Forecaster** | `GradientBoostingRegressor` (150 trees, lr=0.1) | `predictor.py` | Predict AQI at future timestamps | hour, day, lag_1h, lag_3h, wind, temp, traffic |
| **Spatial AQI Estimator** | `RandomForestRegressor` (50 trees) + `KDTree` | `spatial_interpolator.py` | Estimate AQI at any road segment from sparse sensors | distance_to_sensor, sensor_value, is_motorway |
| **Ventilation Predictor** | `RandomForestRegressor` (50 trees) | `ventilation.py` | Predict breathing rate (V_E L/min) by mode | mode, speed_kmh, incline_pct |

---

## 19. All Mathematical Formulas Used (Slide 21)

| Formula | Location | Equation |
|---------|----------|----------|
| **Weighted Fusion** | `fusion_engine.py` | `Fused = 0.6 × Sensor + 0.4 × API` |
| **AQI Penalty** | `basic_router.py` | `Penalty = time × (1 + AQI × sensitivity / 100)` |
| **Haversine Distance** | `basic_router.py` | `d = 2R × atan2(√a, √(1−a))` where `a = sin²(Δφ/2) + cos(φ₁)cos(φ₂)sin²(Δλ/2)` |
| **PM2.5 from AQI** | `ventilation.py` | Piecewise linear: `12/50×AQI` (≤50), `(35.4−12.1)/50×(AQI−50)+12.1` (≤100) |
| **PM2.5 Inhaled** | `ventilation.py` | `µg = (PM2.5_µg/m³ / 1000) × V_E × minutes` |
| **Cigarette Equiv.** | `evaluator.py` | `cigs = PM2.5_saved_µg / 22.0` |
| **Prediction Damping** | `predictor.py` | `w = max(0, 1 − hours/24); result = w×current + (1−w)×predicted` |
| **Spatial Drift** | `spatial_interpolator.py` | `drift = (50 − base) × (dist / 5000)` |
| **Degrees to Meters** | `spatial_interpolator.py` | `meters ≈ degrees × 111,000` |

---

## 20. How to Run (Slide 22)

### First-Time Setup
```bash
# 1. Create virtual environment
python -m venv test_env
test_env\Scripts\activate       # Windows

# 2. Install dependencies
pip install -r requirements.txt

# 3. Download road network data (one-time, ~30 min)
python src/data/download_graph.py --place "Bengaluru, India" --base data/bengaluru
python src/data/download_graph.py --place "Amsterdam, Netherlands" --base data/amsterdam

# 4. Backfill 2 years of AQI history for ML training
python scripts/backfill_data.py
```

### Running the Application
```bash
# Start the server
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000

# Open browser → http://localhost:8000
```

### Running in Demo Mode (no APIs/graphs needed)
```bash
# Start with demo mode enabled
AIRROUTE_DEMO_MODE=true python -m uvicorn src.main:app --port 8000

# Or toggle at runtime:
# POST http://localhost:8000/demo/config {"enabled": true}
```

---

## 21. Presentation Talking Points (Slide 23)

1. **Problem**: Google Maps finds fastest routes, but ignores air quality. Cyclists and pedestrians inhale 2-3× more pollution than car passengers.

2. **Solution**: AirRoute computes two routes and quantifies the health trade-off in **cigarette equivalents** — a metric anyone can understand.

3. **Technical Stack**: Python + FastAPI backend, Leaflet.js frontend, 3 ML models (Gradient Boosting, Random Forest, KDTree), 4 real-time AQI APIs.

4. **Key Formula**: PM2.5 inhaled = f(AQI, breathing_rate, travel_time) → expressed as fraction of a cigarette.

5. **Resilience**: System gracefully degrades from full API data → partial → cached → safe defaults. Never crashes.

6. **Demo Mode**: Simulates all edge cases (API failures, timeouts, empty data) for testing without live infrastructure.
