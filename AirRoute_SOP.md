# AirRoute: Smart Pollution-Aware Navigation System
### Standard Operating Procedure
**Orion Nano Platform | Amsterdam, Netherlands | Version 1.0**

---

### Document Information
| Field | Details |
| :--- | :--- |
| **Status** | DRAFT |
| **Target Hardware** | Orion Nano (ARM Cortex-A57) |
| **Target City** | Amsterdam, Netherlands |
| **Language** | Python 3.10+ |

---

## 1. Purpose & Scope
AirRoute is an embedded navigation system running on the Orion Nano single-board computer. It calculates real-time and predictive routes across a city — differentiated for cars, cyclists, and pedestrians — by fusing live air quality sensor readings with redundant public APIs.

Every route recommendation includes both a fastest route and an air-quality-optimised route, along with a measurable metric explaining whether the air-quality detour is worth taking. The scope of this document covers: system architecture, sensor integration, API management, routing logic, prediction engine, mode-specific behaviour, and university-level enhancement recommendations.

## 2. Target City — Amsterdam, Netherlands
Amsterdam was selected as the reference city due to its best-in-class data infrastructure for this exact type of project:

| Criterion | Amsterdam Specifics |
| :--- | :--- |
| **Open Data Portal** | data.amsterdam.nl — real-time traffic, road closures, cycling infra, pedestrian zones |
| **Air Quality APIs** | RIVM (national) and Luchtmeetnet (city) — both free, documented, updated frequently |
| **Cycling Infrastructure** | 500+ km of dedicated lanes; OSM data is exceptionally detailed |
| **Pedestrian Zones** | Clearly mapped pedestrian-only areas through official GIS datasets |
| **Traffic API** | NDW (national databank wegverkeersgegevens) provides live sensor data at major junctions |
| **Hardware Friendly** | Strong expat/maker community; Orion Nano deployable on lamp posts legally with permit |

## 3. System Architecture

### 3.1 Hardware
* Orion Nano (ARM Cortex-A57, 4 GB RAM, runs Ubuntu 20.04 or JetPack)
* MQ-135 or SDS011 particulate sensor (PM2.5/PM10) on GPIO/UART
* MQ-7 for CO detection (optional secondary sensor)
* GPS module (NEO-6M via UART) for device position
* 4G/LTE dongle or Ethernet for API access
* Weatherproof enclosure rated IP65

### 3.2 Software Stack
| Layer | Technology |
| :--- | :--- |
| **OS** | Ubuntu 20.04 LTS or Jetson Linux (L4T) |
| **Language** | Python 3.10+ |
| **Routing Engine** | OSRM or Valhalla (local, offline-capable) |
| **Graph Library** | NetworkX or OSMnx for road network manipulation |
| **API Scheduler** | APScheduler (interval-based polling) |
| **Data Store** | SQLite (local cache) + optional InfluxDB for time-series |
| **ML Prediction** | scikit-learn or Prophet (time-series forecasting) |
| **Sensor Interface** | PySerial / RPi.GPIO / smbus2 |
| **Web Interface** | FastAPI (optional local dashboard) |

### 3.3 Data Flow
1. Sensor reads air quality every configurable interval (default: 5 min)
2. API Poller pings up to 3 public APIs hourly; if 304 Not Modified or equivalent, skips processing
3. Fusion Engine combines sensor readings with API averages (weighted blend)
4. AQI grid is projected onto the road graph as edge weights
5. Routing Engine solves for (a) fastest path and (b) best air quality path
6. Evaluator computes whether the quality detour is worth it
7. Prediction Engine uses historical logs to forecast air quality for the next 1-6 hours
8. Output returned as JSON with full metrics

## 4. Air Quality Subsystem

### 4.1 Sensor Integration
The onboard sensor provides hyperlocal readings at the installation point. Readings are taken continuously and averaged over a 5-minute window to smooth noise. The sensor pipeline:
* Read raw voltage/serial data from sensor
* Convert to concentration (μg/m³ for PM sensors, ppm for gas sensors)
* Compute AQI using US EPA or EEA breakpoint tables
* Tag each reading with GPS coordinates and timestamp
* Store to local SQLite for prediction model training

### 4.2 Public API Strategy
Three public APIs are queried to provide city-wide coverage beyond the sensor footprint:

| API | Details |
| :--- | :--- |
| **Luchtmeetnet (NL)** | Official Dutch air quality network — JSON REST — updated hourly — free, no key required |
| **OpenAQ** | Aggregates global stations — hourly updates — free tier 60 req/min — JSON |
| **IQAir / AirVisual** | Backup commercial API — free tier 10,000 calls/month — covers gaps in public data |

#### 4.2.1 Smart Polling Logic
The poller runs hourly by default. Before each pull it checks the API's `Last-Modified` or equivalent header:
* If data is unchanged (HTTP 304 or ETag match), skip processing and reschedule
* If an API signals daily updates only (e.g., no intraday changes detected over 24 hrs), the poller automatically drops to a daily schedule for that API to save resources
* If one API returns a 4xx/5xx error or timeout, the system marks it degraded and routes all requests through the remaining two APIs with a warning log
* If two APIs are down simultaneously, the system falls back to sensor-only mode and flags outputs accordingly

### 4.3 Sensor-API Fusion
The final AQI value used for routing is a weighted blend:

> `Final_AQI = (w_sensor * AQI_sensor) + (w_api * AQI_api_mean)`
> 
> **Default weights:** `w_sensor` = 0.6, `w_api` = 0.4
> **If sensor unavailable:** `w_sensor` = 0, `w_api` = 1.0 (normalized across available APIs)
> **If all APIs down:** `w_sensor` = 1.0, `w_api` = 0.0 (output flagged `SENSOR_ONLY`)

## 5. Routing Engine

### 5.1 Road Network Model
The city road graph is downloaded from OpenStreetMap via OSMnx and cached locally. Each edge (road segment) carries:
* Base travel time (distance / speed limit)
* Road type tag (motorway, cycleway, footway, etc.)
* Interpolated AQI score — projected from the nearest sensor/API measurement point
* Mode-access flag (`car_allowed`, `bike_allowed`, `pedestrian_allowed`)

### 5.2 User Modes
| Mode | Behaviour |
| :--- | :--- |
| **Car** | Uses roads with `car_allowed=True` only. Optimises for time on fastest path. AQI path avoids PM2.5 hotspots on major arterials. |
| **Cyclist** | Uses cycleways preferentially; shared roads allowed. AQI weighting is higher because cyclists have greater respiratory exposure than car occupants. |
| **Pedestrian** | Restricted to footways, shared paths, and pedestrian zones. AQI sensitivity is highest. Also avoids noise/crowd hotspots if data is available. |

### 5.3 Dual-Route Output
Every query returns two routes:
* **Route A — Fastest:** Dijkstra/A* on time-weighted graph. Standard GPS-style result.
* **Route B — Best Air Quality:** Modified edge weights where AQI score contributes a penalty. Solver finds the Pareto-optimal path balancing time and air exposure.

Each route output includes:
* Total distance (km)
* Estimated travel time (min)
* Mean AQI along route
* Peak AQI segment (worst point)
* Cumulative exposure index (AQI × time, a proxy for dose)
* Data source flags (`SENSOR`, `API_FULL`, `SENSOR_ONLY`, `DEGRADED`)

### 5.4 Worth-It Evaluator
After computing both routes, the system calculates a recommendation score:

> `Time_penalty = (Route_B_time - Route_A_time)` in minutes
> `Exposure_saving = (Route_A_exposure - Route_B_exposure)`
> `Worth_It = True` if `Exposure_saving` > threshold AND `Time_penalty` < tolerance
> 
> **Default:** threshold = 15 AQI-minutes, tolerance = 10 minutes
> **Output includes:** recommendation, time cost, exposure saving, and plain-English reason.
> 
> *Example:* 'Taking the air-quality route saves 22 AQI-min of exposure at a cost of 4 min extra travel. Recommended for cyclists.'

## 6. Prediction Engine
Historical sensor and API readings stored in SQLite are used to train a lightweight time-series model:
* **Model:** Facebook Prophet (handles seasonality and missing data well on embedded hardware) or scikit-learn Random Forest Regressor as a simpler fallback
* **Features:** hour of day, day of week, historical AQI at same time, wind speed (from Open-Meteo free API), temperature
* **Prediction horizon:** 1 hour, 3 hour, and 6 hour forecasts
* Model is retrained weekly using the accumulated local database
* Predictions are served alongside real-time data so users can plan ahead

> **Example Prediction Output:**
> * Current AQI (sensor+API): 68 — Moderate
> * Forecast in 1 hr: 52 — Moderate (improving, rush hour ending)
> * Forecast in 3 hrs: 41 — Good
> * Recommendation: 'Air quality will improve significantly in 3 hours. If trip is flexible, delaying is advised for cyclists and pedestrians.'

## 7. Output Specification

### 7.1 JSON Response Format
| Field | Type | Description |
| :--- | :--- | :--- |
| `route_fastest` | GeoJSON | Fastest path geometry and waypoints |
| `route_quality` | GeoJSON | Best air quality path geometry and waypoints |
| `fastest.time_min` | float | Estimated travel time in minutes |
| `fastest.aqi_mean` | int | Average AQI along fastest route |
| `quality.time_min` | float | Estimated travel time for quality route |
| `quality.aqi_mean` | int | Average AQI along quality route |
| `worth_it` | bool | Whether quality route is recommended |
| `worth_it_reason` | string | Human-readable explanation |
| `data_source` | string | SENSOR / API_FULL / DEGRADED / SENSOR_ONLY |
| `forecast_1h` | int | Predicted AQI in 1 hour |
| `forecast_3h` | int | Predicted AQI in 3 hours |
| `user_mode` | string | car / cyclist / pedestrian |

## 8. Failure Modes & Fallbacks
| Failure Scenario | System Response |
| :--- | :--- |
| **Sensor hardware failure** | Fall back to API-only mode. Flag output `SENSOR_UNAVAILABLE`. Log error and trigger alert. |
| **1 of 3 APIs unreachable** | Continue with remaining 2 APIs. Log degraded status. Increase retry interval to avoid hammering. |
| **2 of 3 APIs unreachable** | Sensor-only mode. Output flagged `DEGRADED`. Reduce route confidence score. |
| **All 3 APIs + sensor down** | Serve last known cached values (<24 hrs). Flag `CACHE_ONLY`. Do not serve routes if cache >24 hrs old. |
| **Routing engine crash** | Catch exception, return error JSON. Restart OSRM subprocess automatically. |
| **GPS unavailable** | Use installation coordinates as fixed reference. Log warning. |
| **Disk full (SQLite)** | Prune records older than 90 days. Alert operator via log. |

## 9. Development Phases

### Phase 1 — Foundation (Weeks 1-4)
* Set up Orion Nano with Ubuntu and Python environment
* Connect and test air quality sensor; validate readings against reference AQI data
* Download Amsterdam OSM graph and cache locally with OSMnx
* Implement basic A* routing for a single mode (car first)

### Phase 2 — API & Fusion (Weeks 5-8)
* Integrate all 3 public APIs with smart polling and fallback logic
* Implement sensor-API fusion formula
* Project AQI values onto road graph as edge weights
* Build dual-route solver and Worth-It Evaluator

### Phase 3 — Multi-Mode & Prediction (Weeks 9-12)
* Add cyclist and pedestrian mode logic and road filtering
* Build SQLite logging and data accumulation pipeline
* Train and integrate Prophet forecasting model
* Structured JSON output and local FastAPI endpoint

### Phase 4 — Testing & Hardening (Weeks 13-16)
* Stress test all failure modes (simulate API outages, sensor disconnects)
* Validate route recommendations against manual checks in Amsterdam map
* Power consumption profiling on Orion Nano
* Documentation, deployment guide, and academic write-up

## 10. University Project — Recommended Additions & Removals

### 10.1 Strong Additions
* **A. Formal Evaluation Framework:** Uni projects need measurable success criteria. Define: RMSE of AQI predictions vs. ground truth, time overhead of quality route vs. fastest (%), user study (5-10 participants navigating both routes), comparison of routing outcomes with and without prediction module. This transforms the project from a build into a research contribution.
* **B. Ethics & Privacy Section:** Sensors and GPS in urban spaces raise questions about incidental data collection (e.g., could pedestrian counts reveal personal movement?). A short section on data minimisation, anonymisation, and GDPR compliance (especially relevant for Netherlands/EU) would significantly impress examiners.
* **C. Comparative Baseline:** Compare AirRoute against Google Maps or Citymapper outputs for the same journeys. If your quality route is genuinely better for air exposure, that is a concrete, defensible research result.
* **D. Noise Pollution Layer (Optional Extension):** Amsterdam publishes noise maps. Adding noise as a secondary optimisation dimension (weight alongside AQI) would differentiate pedestrian routing substantially and is a natural extension that shows system extensibility.

### 10.2 Suggested Removals / Simplifications
* Remove IQAir from Phase 1 — start with just Luchtmeetnet and OpenAQ; add the third API once the two-API fallback logic is proven
* Simplify fusion weights initially — start with 50/50 blend, tune with empirical data later rather than setting arbitrary 0.6/0.4
* Defer pedestrian noise optimisation to an extension chapter, not core scope — keeps the core deliverable tractable for a semester project
* Do not attempt to run OSRM and Prophet concurrently on Orion Nano in real-time — pre-compute route graphs and update them on a schedule instead (memory constraint)

### 10.3 Academic Framing
Frame the project under one of these research questions to sharpen the write-up:
* 'Can hyperlocal sensor fusion with public API data produce meaningfully better air-quality-aware routes than API data alone?'
* 'Does mode-differentiated air quality routing produce measurably different route recommendations, and are those differences health-relevant?'
* 'How accurately can an embedded time-series model predict urban AQI fluctuations sufficient for proactive routing advice?'

## 11. Reference APIs & Libraries
| Resource | URL / Package |
| :--- | :--- |
| **Luchtmeetnet API** | api.luchtmeetnet.nl |
| **OpenAQ API** | api.openaq.org |
| **IQAir API** | api.airvisual.com |
| **OSMnx** | pip install osmnx |
| **Prophet** | pip install prophet |
| **APScheduler** | pip install apscheduler |
| **FastAPI** | pip install fastapi uvicorn |
| **OSRM** | github.com/Project-OSRM/osrm-backend |
| **Amsterdam Open Data** | data.amsterdam.nl |
| **Open-Meteo (weather)** | api.open-meteo.com |