# AirRoute: Technical Implementation & Security Analysis

This document provides a comprehensive breakdown of the AirRoute system, explaining the architectural choices, library selection rationale, core mechanisms, and security infrastructure.

---

## 1. Core Technology Stack & Imports

The following libraries form the backbone of AirRoute. Each was selected based on specific performance and integration requirements.

### Web Framework: FastAPI
*   **Import**: `from fastapi import FastAPI`
*   **Why chosen over Flask/Django**: 
    *   **Asynchronous Performance**: FastAPI is built on Starlette and Uvicorn, allowing for non-blocking I/O. Since AirRoute performs heavy routing calculations and multiple API fetches, `async` support prevents the server from freezing during long-running tasks.
    *   **Pydantic Integration**: Automatic data validation and serialization.
    *   **Auto-Documentation**: Generates Swagger/OpenAPI docs natively, speeding up frontend-backend integration.

### Geospatial Logic: OSMnx & NetworkX
*   **Imports**: `import osmnx`, `import networkx`
*   **Why chosen over OSRM or GraphHopper**:
    *   **Weight Flexibility**: Unlike OSRM (which requires C++ profile modification), OSMnx allows us to dynamically change edge weights (e.g., adding "Pollution Tax" to paths) using pure Python.
    *   **Ease of Setup**: OSRM requires significant infrastructure; OSMnx downloads and builds the graph into memory from OpenStreetMap data, making it ideal for portable, city-specific deployments.

### Data Science: Scikit-learn (Random Forest)
*   **Import**: `from sklearn.ensemble import RandomForestRegressor`
*   **Why chosen over Neural Networks**:
    *   **Efficiency**: AQI data is tabular and temporal. Random Forests handle these relationships exceptionally well without the massive computational overhead of Deep Learning.
    *   **Interpretability**: It allows us to understand feature importance (e.g., how much "Time of Day" impacts "PM2.5").

### Data Handling: Pandas & Requests
*   **Imports**: `import pandas`, `import requests`
*   **Rationale**: Pandas is the industry standard for time-series cleaning (crucial for AQI backfilling), while `requests` is used for its simplicity in handling multi-source API polling.

---

## 2. System Mechanism: How It Works

AirRoute operates as a 3-layer pipeline: **Sensing**, **Fusion**, and **Routing**.

### Layer 1: Multi-Source Sensing
The `AQIManager` polls 4 different international APIs (Luchtmeetnet, OpenAQ, WAQI, IQAir). This provides redundancy. If one API goes down, the system enters "Degraded Mode" rather than failing.

### Layer 2: The Fusion Engine
The `FusionEngine` takes "Ground Truth" (local hardware sensor data) and "Global Data" (public APIs). It uses a weighted fusion algorithm:
1.  If a local sensor is present, it uses a 70/30 weight split (local data is more relevant to the user's immediate vicinity).
2.  If local sensors fail, it switches to a weighted average of API data.

### Layer 3: Pollution-Aware Routing
The system uses **Dijkstra’s Algorithm** with a custom cost function:
*   **Fastest Route**: Weight = `length` (meters).
*   **Cleanest Route**: Weight = `length * (1 + NormalizedAQI)`.
By "taxing" polluted streets, the algorithm naturally finds paths through parks or residential areas with lower traffic density.

---

## 3. Security Architecture & Implementation

Security in AirRoute is built on the principle of **Defensive Programming** and **Input Hardening**.

### A. Input Sanitization & Validation (Pydantic)
Every request to the `/route` endpoint is filtered through a Pydantic Model. 
*   **Mechanism**: If a user sends a string instead of a float for `lat`, the request is rejected *before* it reaches the logic layer.
*   **Why**: This prevents "Injection Attacks" where malicious payloads might be passed into underlying OS commands or library calls. It also ensures that the routing engine (OSMnx) doesn't crash on invalid coordinate inputs.

### B. Fail-Safe Operations (Graceful Degradation)
The `AQIManager` uses a `fetch_all_safe()` wrapper.
*   **Mechanism**: All API calls are wrapped in `try-except` blocks with strict timeouts (10s) using the `requests` library. 
*   **Why**: This prevents **Denial of Service (DoS)** scenarios where the backend hangs indefinitely waiting for a timed-out external server. If all APIs fail, the system serves cached data (`CACHE_ONLY` status). This ensures the application remains "Always-On" regardless of external internet conditions.

### C. Resource Lock & Concurrency Control
AirRoute uses a `threading.Lock()` for lazy-loading city routers.
*   **Mechanism**: When a city (e.g., Bengaluru) is requested the first time, a lock is acquired. 
*   **Why**: This prevents **Resource Exhaustion**. Loading a city involves downloading a multi-megabyte OpenStreetMap graph and parsing it into memory. Without a lock, 100 simultaneous requests for a new city would trigger 100 simultaneous downloads, potentially crashing the server's RAM and CPU. The lock ensures only *one* load happens at a time.

### D. Demo Mode: Request Isolation & Security
The `DemoModeMiddleware` intercepts requests at the Starlette layer before they reach the controller logic.
*   **Mechanism**: If `demo_mode` is enabled, the middleware bypasses the real backend entirely and injects mock JSON responses.
*   **Why**: This provides a "Sandbox" environment. It allows public demonstrations to run without consuming real API quotas, exposing real API keys in network logs, or allowing unauthorized writes to the persistent logging system.

### E. Security Gap Analysis: Credential Management
*   **Current State**: AirRoute currently uses hardcoded API keys for WAQI and IQAir in `aqi_service.py` for ease of "One-Click Deployments."
*   **Security Best Practice (Future Proofing)**: In a production environment, these are moved to `.env` files and loaded via `python-dotenv`. This prevents keys from being committed to version control (Git) and allows for "Secret Rotation" without modifying source code.

### F. Data Privacy & Anonymization
The architecture follows **Privacy-by-Design** principles.
*   **Mechanism**: The `AQILogger` records global city AQI snapshots, but *never* logs user traces.
*   **Why**: By design, AirRoute does not store `UserID`, `ExactStartLocation`, or `Destination`. The routing happens in-memory and is discarded after the response. This ensures compliance with modern privacy standards (GDPR/CCPA) by never collecting PII (Personally Identifiable Information).

---

## 4. Why this Security Model?

We chose a **Backend-Heavy Security Model**. Instead of relying on the browser to "behave" or users to provide "clean" data, the Backend treats every incoming packet as potentially malicious. 

1.  **Pydantic** eliminates Data Integrity risks.
2.  **Thread Locks** eliminate Resource Starvation risks.
3.  **Cache Fallbacks** eliminate Availability risks.
4.  **Middleware** eliminates Data Exposure risks during demos.

By combining these layers, AirRoute maintains a high "Resilience Profile" even when running on low-resource hardware or unstable network environments.
