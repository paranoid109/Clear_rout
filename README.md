# AirRoute: Smart Pollution-Aware Navigation

AirRoute is a high-end navigation system designed to optimize urban travel by balancing **speed** and **air quality**. It fuses real-time data from four live APIs with the OpenStreetMap road network to provide a safer, cleaner commute for drivers, cyclists, and pedestrians.

## 🌟 Features
- **Dual-Route Solver**: View the "Fastest" vs. "Cleanest" routes side-by-side.
- **Web Dashboard**: Interactive Leaflet.js map with glassmorphic dark-mode aesthetics.
- **Multi-Source Fusion**: Live data from Luchtmeetnet (NL), WAQI, OpenAQ v3, and IQAir.
- **Prediction Engine**: Forecasts AQI trends for the next 1h and 3h horizons.
- **Resilient Core**: Automatic fallbacks to local sensor data and SQLite caches.

## 🚀 Getting Started

### 1. Prerequisites
- **Python 3.10+** (Recommended: 3.13)
- Internet connection (for graph initialization and live API fetching)

### 2. Installation
```powershell
pip install -r requirements.txt
```

### 3. Data Initialization
Download the Amsterdam road network (one-time setup):
```powershell
python src/data/download_graph.py
```

## 🖥️ Using the Dashboard

1.  **Start the Server**:
    ```powershell
    $env:PYTHONPATH="."; python src/main.py
    ```
2.  **Access in Browser**:
    Navigate to **http://localhost:8000**
    
3.  **How to Route**:
    - Select your **Mode** (Car, Bike, or Walk).
    - **Click the Map** to set your Start point (Blue Marker).
    - **Click again** to set your Destination (Red Marker).
    - Review the **Route Insights** panel for AQI savings and time trade-offs.

## 🧪 Testing & Verification

- **Full Verification**: `python scripts/verify_phase3.py`
- **Resilience Check**: `python scripts/test_resilience.py`
- **Interactive API Docs**: `http://localhost:8000/docs`

---
**Amsterdam Smart Navigation | Version 1.1 (Dashboard Edition)**
