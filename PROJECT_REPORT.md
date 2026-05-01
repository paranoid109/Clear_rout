# AirRoute: Pollution-Aware Smart Navigation
## Project Explainer & Panel Presentation Guide

### 1. Executive Summary
**AirRoute** is a high-end navigation system that solves a critical urban health problem: standard GPS (like Google Maps) optimizes for speed, often leading users through highly polluted corridors. AirRoute fuses real-time data from 4 global APIs and local hardware sensors to calculate a **"Cleanest Route"** alongside the fastest one. It uses advanced machine learning to predict AQI trends and physiological models to translate pollution exposure into a relatable metric: **"Cigarette Equivalence."**

---

### 2. How the Project Works (Technical Architecture)

#### A. Data Acquisition & Fusion
- **Multi-Source API Fusion**: The system pulls live air quality data from **Luchtmeetnet (Netherlands)**, **WAQI (Global)**, **OpenAQ v3**, and **IQAir**.
- **Hardware Integration**: Supports local MQ-135/SDS011 sensors.
- **Weighted Fusion Engine**: Blends API and Sensor data (default 60% sensor, 40% API) to create a trusted "Hyperlocal AQI" value.
- **Graceful Degradation**: If APIs fail, the system falls back to cached data or safe defaults, ensuring it never crashes.

#### B. The Intelligence Layer (Machine Learning)
1. **AQI Forecasting**: A **Gradient Boosting Regressor** predicts pollution levels at +1h, +3h, and +7d horizons using weather features (wind, temp) and historical lag data.
2. **Spatial Interpolation**: Uses a **KDTree** for fast nearest-neighbor lookups and a **Random Forest Regressor** to estimate street-level AQI between sparse sensor stations.
3. **Physiological Inhalation Model**: A Random Forest model predicts **Minute Ventilation (V_E)** — how much air you breathe per minute — based on your transport mode (Car, Bike, Walk) and exertion level.

#### C. The Routing Engine
- Built on **OpenStreetMap (OSMnx)** and **NetworkX**.
- **Mode-Specific Sensitivity**: Pedestrians and cyclists are weighted more heavily for pollution exposure (2.0x and 1.5x respectively) compared to car passengers.
- **Penalty Logic**: Every road segment is assigned an `aqi_penalty`. The "Cleanest Route" is found by minimizing the total penalty (Time × AQI Impact) using Dijkstra's algorithm.

---

### 3. Key Innovation: The "Cigarette Metric"
To make abstract AQI numbers meaningful, the system calculates the exact mass (micrograms) of PM2.5 inhaled during a trip. 
- **The Formula**: `PM2.5_Inhaled = Concentration (µg/m³) × Breathing_Rate (L/min) × Time (min)`
- **The Translation**: 22 micrograms of PM2.5 is roughly equivalent to smoking 1 cigarette.
- **The Impact**: The dashboard tells the user: *"Taking the clean route saves you from inhaling the equivalent of 1.2 cigarettes of smog."*

---

### 4. Panel Presentation Strategy

#### Slide-by-Slide Outline
| Slide | Focus | Key Talking Point |
| :--- | :--- | :--- |
| **1. Intro** | Problem Statement | "Google Maps finds the fastest way to get there, but often the most toxic." |
| **2. Solution** | AirRoute Overview | "A navigation system that treats clean air as a priority, not an afterthought." |
| **3. UI/UX** | Dashboard Design | "Glassmorphic dark-mode dashboard providing side-by-side route comparisons." |
| **4. Backend** | Data Fusion | "How we blend 4 global APIs with local sensors for 99.9% data reliability." |
| **5. ML Models** | Forecasting & Interpolation | "Moving from station-level data to street-level intelligence using Random Forests." |
| **6. Physiology** | Breathing & Impact | "Why a cyclist needs a different route than a driver (Minute Ventilation)." |
| **7. The Metric** | Cigarette Equivalence | "Turning complex data into a metric anyone understands: Cigarettes saved." |
| **8. Conclusion** | Future Scope | "Expansion to more cities and integration with smart wearable health data." |

#### Potential Q&A Questions
- **Q: How accurate is the spatial interpolation?**
  - **A**: We use Random Forest regression trained on distance-to-sensor and road type (highways vs. residential). This allows us to estimate pollution gradients even in areas without sensors.
- **Q: Why Gradient Boosting for forecasting instead of LSTM?**
  - **A**: For tabular time-series data with weather features, Gradient Boosting is more compute-efficient and provides better performance on sparse historical data compared to deep learning models like LSTMs.
- **Q: What happens if the internet goes down?**
  - **A**: The system's **Resilient Core** uses local SQLite caches of the last 90 days of AQI data and pre-downloaded road networks to continue functioning offline.

---

### 5. Live Demo Script
1. **Show the Map**: Point out the dark-themed Leaflet map of Amsterdam/Bengaluru.
2. **Select Mode**: Change from 'Car' to 'Walk' and explain how the routes shift to avoid main roads.
3. **Set Points**: Click a start and destination.
4. **Compare**: Highlight the "Route Insights" panel. Show the time difference (e.g., +2 mins) versus the air quality gain (e.g., -30% AQI).
5. **The Punchline**: Point to the recommendation: *"Worth it! Saves 0.8 cigarettes of exposure."*

---
**Report Generated for Aditya | AirRoute V1.1**
