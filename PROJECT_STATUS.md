# AirRoute Project Status & Technical Overview

This document provides an in-depth breakdown of the current state of the **AirRoute** smart pollution-aware navigation system, the technology stack utilized, what has been completed, and what remains to be implemented according to the Standard Operating Procedure (SOP).

## 🛠️ Technology Stack Used

### 1. Backend / Server
- **Framework**: `FastAPI` with `Uvicorn` ASGI server (high performance, lightweight).
- **Language**: Python 3.10+
- **Database**: `SQLite` for local time-series data buffering and historical measurements cache (`air_quality_history.db`).

### 2. Core Engines
- **Routing Engine**: `OSMnx` and `NetworkX` used to download, manipulate, and route through OpenStreetMap graphs. Utilizes Dijkstra/A* pathfinding algorithms modified for multi-objective optimization (time vs. AQI exposure).
- **Prediction Engine**: `scikit-learn` (`LinearRegression`) and `pandas` currently used for time-series forecasting of 1h and 3h AQI metrics based on historical database hour-of-day features.
- **Fusion Engine**: Custom lightweight aggregator (`FusionEngine`) that blends live hardware sensor readings with averaged fallback Web API data based on confidence weights.

### 3. API & Data Layer
- **Requests Layer**: Python `requests` library.
- **Live Data Sources**: 
  - `Luchtmeetnet` API (Dutch National)
  - `OpenAQ v3` API
  - `IQAir` API
  - `WAQI` API
- **Smart Fallback**: The `AQIManager` gracefully degrades through stages (`API_FULL` → `DEGRADED` → `CACHE_ONLY`) if individual data sources time out or return errors.

### 4. Frontend Web App
- **Structure**: Vanilla Next-Gen HTML5 structure.
- **Styling**: Pure CSS (Vanilla) utilizing modern visual techniques: CSS Variables for theming (`--bg-dark`, `--accent-blue`), glassmorphism via `backdrop-filter: blur`, flexbox/grid for responsive layouts, taking heavy inspiration from premium interface design patterns.
- **Interactivity**: Vanilla JavaScript `app.js` with `fetch` API bridging UI interaction with the FastAPI backend.
- **Map Visualization**: `Leaflet.js` using CartoDB Dark tile layers and dynamic `GeoJSON` polylines for route charting.

---

## ✅ What is Completed

### Foundation & Data Engineering
- [x] **Project Structure**: Clean modular architecture separating routing, prediction, api retrieval, and data aggregation.
- [x] **API Connections**: Complete integration with OpenAQ, WAQI, IQAir, and Luchtmeetnet with proper API key header injection, exception management, and json caching.
- [x] **Sensor Fusion System**: Working pipeline that fuses local `MockAQISensor` data with aggregated macro-API data and writes periodic readings to `SQLite` history logs.
- [x] **Server Fixing**: Resolved import (`sys.path`) issues blocking the entrypoint `main.py` from successfully serving the application dynamically.

### Routing Logic
- [x] **Dual-Path Solver**: System resolves **both** the Time-optimized route (Standard GPS) and AQI-optimized route (Quality Path).
- [x] **Worth-It Evaluator**: Complex scoring algorithm calculates exposure savings against travel time penalty to produce an actionable recommendation rating.

### Dashboard / Interface
- [x] **Visual Design**: Premium glassmorphic interface, dynamic mode selectors, clear status badges for routing recommendations.
- [x] **Interactive Maps**: Fully functional mapping surface. Users can drop custom Start and End markers on the map, instantly triggering backend route calculation.
- [x] **Live Polling**: Real Time backend pooling updates the visual widgets showing current Amsterdam city-average AQI and 1h/3h predictions.

---

## 🚧 What Needs to be Completed (Next Steps)

While the product MVP is functional, the following components require implementation to reach **Version 1.0 Production Readiness** as detailed in the `AirRoute_SOP.md`.

### 1. Dynamic Mode-Specific Pathing
- **Current State**: The UI allows toggling between "Car", "Cycle", and "Walk". However, the `AirRouter` defaults to loading the `amsterdam_drive` graph statically across the whole application lifecycle.
- **Required Fix**: Backend needs to dynamically swap `NetworkX` graphs (e.g. `amsterdam_bike.graphml` and `amsterdam_walk.graphml`) depending on the querystring parameter received by `/route`.

### 2. Prophet Integration for Prediction
- **Current State**: Prediction is implemented using a very rudimentary `scikit-learn` `LinearRegression` model using just the hour of the day.
- **Required Fix**: Replace the simple linear function with **Facebook Prophet** or **XGBoost** utilizing external weather API logic (wind scatter, temperature) to boost 3h-horizon accuracy.

### 3. Granular Heatmap Generation (Node Level)
- **Current State**: The API outputs a single unified AQI value for the entire city, meaning "clean" and "fast" routes rely heavily on static edge estimations rather than dynamic zone-based smog avoidance.
- **Required Fix**: Extrapolate individual API node coordinates (`lat/lon` retrieved in `aqi_service.py`) directly onto `ox.graph` nearest edges to create real "hotspots" instead of generalized values.

### 4. Hardware Deployment Migration
- **Current State**: Working as a local web server utilizing `MockAQISensor`. 
- **Required Fix**: Implement PySerial bindings for physical UART MQ-135 sensors to run accurately on the Orion Nano, writing start-scripts and permissions setups for Jetson Linux environments.
