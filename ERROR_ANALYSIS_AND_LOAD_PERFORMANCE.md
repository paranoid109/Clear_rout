# AirRoute: Error Log & Performance Analysis

This document provides a comprehensive summary of the technical hurdles encountered during the development of the **AirRoute** system and an in-depth explanation of why the application experiences significant loading times.

---

## 1. History of Errors Encountered

During the build process, several critical errors and "gotchas" were identified and resolved. These are categorized below:

### A. Integration & Backend Stability
*   **`ModuleNotFoundError` (sys.path issues)**:
    *   **The Error**: Running `python src/main.py` initially failed because the script couldn't find the `src` modules when executed from the root.
    *   **The Fix**: Implemented `sys.path.append('.')` in entry points and transitioned to running the app via `python -m uvicorn src.main:app` from the project root.
*   **API Response Mismatch**:
    *   **The Error**: External APIs (OpenAQ, WAQI) occasionally changed their JSON structure or returned `null` for certain coordinates, causing the fusion engine to crash.
    *   **The Fix**: Created the `AQIManager` with strict validation and "Graceful Degradation." It now uses a chain of logic: `API_FULL` → `DEGRADED` → `CACHE_ONLY`.
*   **Frontend-Backend Sync Failures**:
    *   **The Error**: The Leaflet.js frontend expected a specific GeoJSON format, while the backend was initially returning raw Coordinate tuples, resulting in blank maps.
    *   **The Fix**: Standardized the `RouteResponse` schema using Pydantic to ensure the frontend always receives clean, parseable paths.

### B. Data & Database Logic
*   **SQLite Schema Inconsistency**:
    *   **The Error**: Adding "Multi-City" support (Amsterdam & Bengaluru) caused the logger to fail because the existing database table didn't have a `city` column.
    *   **The Fix**: Implemented a "patch" script to backfill city names and updated the `AQILogger` to handle dynamic table schemas.
*   **Spatial Interpolator "Flatlining"**:
    *   **The Error**: Initially, the "Cleanest Route" was identical to the "Fastest Route" because the system was applying a single AQI average to every road in the city.
    *   **The Fix**: Developed the `SpatialInterpolator` using a **K-D Tree** and **Random Forest Regressor** to estimate street-level AQI based on distance to the nearest sensor and road type (e.g., motorways getting a higher pollution penalty).

### C. Environment & Dependencies
*   **OSMnx/NetworkX Versioning**:
    *   **The Error**: Some versions of `osmnx` changed their graph attribute names, causing `ox.load_graphml` to fail when loading pre-downloaded data.
    *   **The Fix**: Locked dependencies in `requirements.txt` and added a verification script (`scripts/verify_phase3.py`) to check data integrity on startup.

---

## 2. Why does the application take so long to load?

The "Loading..." state in AirRoute is the result of several heavy computational and I/O processes happening in the background.

### 1. Massive Graph Data (I/O Bottleneck)
The system uses high-resolution road networks from OpenStreetMap.
*   **File Sizes**:
    *   `bengaluru_walk.graphml`: **~183 MB**
    *   `bengaluru_bike.graphml`: **~165 MB**
    *   `bengaluru_drive.graphml`: **~150 MB**
*   **Explanation**: When you select a city or transport mode, the backend must load these giant XML-based files into memory. NetworkX builds a complex graph structure with hundreds of thousands of nodes and edges, which is extremely RAM and CPU intensive.

### 2. Spatial Projection (Algorithm Latency)
Before a route can be calculated, the system must "project" live air quality data onto the road network.
*   **The Process**:
    1.  Fetch live data from 4 APIs (Network Latency).
    2.  Use the **K-D Tree** to find the nearest sensor for *every* road segment in the graph.
    3.  Run a **Random Forest** prediction for every edge to estimate pollution.
*   **Latency**: For a city like Bengaluru with 100k+ road segments, even a vectorized NumPy operation takes several seconds to complete the math.

### 3. Dual-Path Dijkstra (Pathfinding Complexity)
Unlike Google Maps which just finds the fastest path, AirRoute runs the search algorithm **twice** per request:
1.  **Path 1**: Weighted by `travel_time`.
2.  **Path 2**: Weighted by `aqi_penalty` (a custom formula combining time, PM2.5 exposure, and physiological breathing rates).
*   **Explanation**: Searching through a graph of that size twice, while calculating "Cigarette Equivalency" for every possible detour, adds substantial calculation overhead.

### 4. Machine Learning Forecasts
On every route request, the system also runs the `AQIPredictor`.
*   **Explanation**: It gathers 2 years of historical data from the SQLite DB, extracts weather features (wind, temp), and runs a **Gradient Boosting Regressor** to predict AQI for +1h and +3h. While the model is fast, the data gathering step from SQL adds a minor delay.

---

## 3. Future Optimization Plan

To fix these loading issues, the following optimizations are planned:
1.  **Lazy Loading**: Only load the graph into memory once (singleton pattern) and keep it cached.
2.  **Binary Formats**: Move from `.graphml` (XML) to `.pickle` or `.geoparquet` for 5x faster file loading.
3.  **Graph Pruning**: Strip away irrelevant road data outside the current bounding box of the user's start/end points.
4.  **WebWorkers**: Offload non-critical predictions to background threads so the map can render the route immediately.
