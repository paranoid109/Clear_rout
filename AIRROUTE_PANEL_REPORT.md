# AirRoute: Smart Pollution-Aware Navigation
## Comprehensive Project Report & Panel Presentation Guide

> **Prepared for**: Academic/Technical Review Panel  
> **Project Version**: 1.1 (Dashboard Edition)  
> **Core Focus**: Urban Health, Machine Learning, and Multi-Source Data Fusion

---

## 1. Project Overview
**AirRoute** is a next-generation navigation system that moves beyond the "fastest path" paradigm of traditional GPS. It solves a critical urban problem: **the hidden health cost of commuting.** 

Standard navigation apps optimize for time, often funneling pedestrians and cyclists through high-pollution corridors (main roads, tunnels). AirRoute calculates a **"Cleanest Route"** alongside the fastest one, providing users with the data they need to make health-conscious travel decisions.

### Key Value Propositions
- **Dual-Route Side-by-Side**: Immediate comparison of Time vs. Air Quality.
- **Physiological Modeling**: Different impact metrics for drivers vs. cyclists (breathing rates).
- **Relatable Metrics**: Translates abstract AQI into "Cigarettes of Smog Saved."
- **Data Resilience**: Never crashes—gracefully degrades during API outages.

---

## 2. Technical Architecture

### A. The Tech Stack
| Layer | Technology | Purpose |
| :--- | :--- | :--- |
| **Frontend** | Vanilla JS, Leaflet.js, CSS3 | Interactive map with glassmorphic dark-mode aesthetics. |
| **Backend** | FastAPI (Python 3.13) | High-performance asynchronous REST API. |
| **Database** | SQLite3 | Local storage for 2 years of historical AQI data. |
| **Routing** | OSMnx, NetworkX | Graph-based navigation using OpenStreetMap data. |
| **ML Engine** | Scikit-Learn | Gradient Boosting & Random Forest models. |

### B. Core Components
1.  **Multi-Source Fusion Engine**: Blends data from 4 global APIs (**Luchtmeetnet, WAQI, OpenAQ, IQAir**) with local hardware sensors. It uses a weighted average (60% sensor, 40% API) to ensure hyperlocal accuracy.
2.  **Spatial Interpolator**: Uses a **KDTree** and **Random Forest** to estimate street-level pollution gradients where sensors are missing. It automatically penalizes motorways and trunk roads.
3.  **AQI Forecasting**: A **Gradient Boosting Regressor** predicts pollution trends for the next 1h, 3h, and 7 days, allowing users to plan cleaner trips in advance.
4.  **Ventilation Model**: A physiological model that calculates **Minute Ventilation (V_E)**—the actual volume of air inhaled based on transport mode and effort.

---

## 3. The "Cigarette Equivalence" Innovation
The most significant barrier to pollution-aware navigation is that **AQI numbers are abstract.** A user doesn't know if "AQI 85" is worth a 5-minute detour.

AirRoute solves this by calculating the **exact mass of PM2.5 inhaled** during the trip:
- **Formula**: `Mass (µg) = Concentration (µg/m³) × Breathing Rate (L/min) × Trip Duration (min)`
- **Conversion**: Based on medical research, **22µg of PM2.5 inhalation ≈ 1 Cigarette.**
- **Output**: The dashboard tells the user: *"Taking the Cleanest Route saves you the equivalent of 1.4 cigarettes of smog exposure."*

---

## 4. Panel Presentation Guide (Slide-by-Slide)

### Slide 1: The Problem
*   **Visual**: Photo of a cyclist behind a bus in heavy traffic.
*   **Point**: "Traditional GPS is blind to air quality. We treat speed as the only metric, but for active commuters (walkers/cyclists), the health cost of the 'fastest' route can be higher than the time benefit."

### Slide 2: The Solution (AirRoute)
*   **Visual**: Screenshot of the side-by-side route comparison.
*   **Point**: "AirRoute provides two paths. We don't force a choice; we provide the data. Cleanest vs. Fastest."

### Slide 3: Intelligence & ML
*   **Visual**: A diagram showing Sensor + API → Fusion → Graph Penalty.
*   **Point**: "We use three distinct ML models. One for forecasting (Gradient Boosting), one for street-level interpolation (Random Forest), and one for human physiology (Ventilation Prediction)."

### Slide 4: Real-World Resilience
*   **Visual**: A list of the 4 APIs and a "Degraded Mode" notification.
*   **Point**: "A navigation system cannot fail. If all 4 APIs go down, our system uses local SQLite caches and hardware sensor data to maintain service. It's built for mission-critical reliability."

### Slide 5: Impact & Future
*   **Visual**: The "Cigarettes Saved" icon.
*   **Point**: "By making pollution personal, we drive behavioral change. Future steps include integration with wearable health data (Apple Health/Fitbit) to refine the ventilation model further."

---

## 5. Technical "Cheat Sheet" for Q&A

**Q: Why use Gradient Boosting for forecasting instead of a Neural Network?**
*   **Answer**: "For tabular time-series data with external features (weather/traffic), Gradient Boosting Regressors are more efficient, easier to interpret, and require less training data to reach high accuracy compared to LSTMs or Transformers."

**Q: How do you handle the computational cost of routing with AQI?**
*   **Answer**: "We pre-download the OSM graphs. During a request, we use NumPy for vectorized AQI projection onto road edges. The actual pathfinding uses Dijkstra's algorithm via NetworkX, which is highly optimized for graphs of this scale (Amsterdam/Bengaluru)."

**Q: Is the cigarette metric scientifically accurate?**
*   **Answer**: "It is an approximation based on the Berkeley Earth study which correlates PM2.5 mass to cigarette health impacts. While not a clinical diagnosis, it serves as an effective 'behavioral nudge' to communicate relative risk."

**Q: How does the system handle areas with no sensors?**
*   **Answer**: "Our Spatial Interpolator uses a Random Forest model trained on road types (highway vs. residential) and proximity to known sensors. It 'fills the gaps' by assuming higher pollution on arterial roads compared to residential streets."

---

## 6. Live Demo Script
1.  **Dashboard Reveal**: "Notice the dark-mode, glassmorphic design—built for modern urban users."
2.  **The Comparison**: "I'll select 'Walk' from Dam Square to Rijksmuseum. Notice how the 'Fastest' route takes us along the main canal roads, while the 'Cleanest' route weaves through quieter residential streets."
3.  **The Decision**: "The Cleanest route adds 3 minutes, but look at the insights panel: It saves 0.9 cigarette equivalents of PM2.5. For a daily commuter, that's nearly 5 cigarettes a week—a significant health gain."

---
**AirRoute: Clean Air as a Priority.**  
*Generated for Panel Review | April 2026*
