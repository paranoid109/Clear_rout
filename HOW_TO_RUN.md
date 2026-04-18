# How to Run AirRoute

---

## Option A: Demo Mode (No APIs, No Graph Data Needed)

Demo mode skips all heavy initialization and returns realistic mock data.  
**Use this for presentations, UI testing, or when you don't have the graph files / API keys.**

### Windows (PowerShell)
```powershell
# 1. Activate the virtual environment
test_env\Scripts\activate

# 2. Start the server in demo mode
$env:AIRROUTE_DEMO_MODE="true"
python -m uvicorn src.main:app --host 127.0.0.1 --port 8000

# 3. Open browser → http://localhost:8000
```

### Windows (CMD)
```cmd
test_env\Scripts\activate
set AIRROUTE_DEMO_MODE=true
python -m uvicorn src.main:app --host 127.0.0.1 --port 8000
```

### Linux / Mac
```bash
source test_env/bin/activate
AIRROUTE_DEMO_MODE=true python -m uvicorn src.main:app --host 127.0.0.1 --port 8000
```

### What Happens in Demo Mode
- Server starts in **< 1 second** (no graph loading, no ML training)
- All API endpoints (`/route`, `/stats`, `/health`) return **mock data**
- **80% of requests** return success, **20% simulate edge cases** (errors, timeouts, empty data)
- Console shows color-coded logs for each simulated scenario

### Controlling Demo Behavior at Runtime

**Force all requests to succeed** (smooth demo):
```
POST http://localhost:8000/demo/config?force_scenario=success
```

**Force a specific edge case**:
```
POST http://localhost:8000/demo/config?force_scenario=error
POST http://localhost:8000/demo/config?force_scenario=timeout
POST http://localhost:8000/demo/config?force_scenario=empty
```

**Change success rate** (e.g., 90% success):
```
POST http://localhost:8000/demo/config?success_rate=0.9
```

**Check current config and stats**:
```
GET http://localhost:8000/demo/config
```

**Turn demo mode OFF** (switch to real backend):
```
POST http://localhost:8000/demo/config?enabled=false
```

---

## Option B: Production Mode (Real APIs + Real Graph Data)

This mode uses live AQI data from 4 APIs and real OpenStreetMap road networks.  
**Requires graph files (~400 MB total) and internet connection.**

### First-Time Setup (One Time Only)

```powershell
# 1. Create and activate virtual environment
python -m venv test_env
test_env\Scripts\activate

# 2. Install all dependencies
pip install -r requirements.txt

# 3. Download road network graphs (~30 min per city)
python src/data/download_graph.py --place "Bengaluru, India" --base data/bengaluru
python src/data/download_graph.py --place "Amsterdam, Netherlands" --base data/amsterdam

# 4. Backfill 2 years of AQI history for ML training
python scripts/backfill_data.py
```

### Starting the Server

```powershell
# 1. Activate the virtual environment
test_env\Scripts\activate

# 2. Start the server (production mode — no demo env var)
python -m uvicorn src.main:app --host 127.0.0.1 --port 8000

# 3. Open browser → http://localhost:8000
```

### What Happens in Production Mode
- Server takes **30–60 seconds** to start (trains ML models on historical data)
- First route request per city takes **10–30 seconds** (lazy-loads the road graph into memory)
- Subsequent requests are fast (< 2 seconds)
- Uses live data from 4 AQI APIs (Luchtmeetnet, OpenAQ, WAQI, IQAir)
- Falls back to cached data if APIs are unavailable

---

## Quick Reference

| | Demo Mode | Production Mode |
|---|-----------|-----------------|
| **Start command** | `$env:AIRROUTE_DEMO_MODE="true"` then `uvicorn` | Just `uvicorn` (no env var) |
| **Startup time** | < 1 second | 30–60 seconds |
| **Needs graph files?** | No | Yes (~400 MB) |
| **Needs internet?** | No | Yes (AQI APIs) |
| **Data source** | Mock (randomized) | Live APIs + sensor |
| **Use for** | Presentations, UI testing, development | Real navigation, testing accuracy |

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Stuck on "Initializing city graph..." | You're in production mode without graph files. Switch to demo mode or download graphs (see First-Time Setup). |
| `ModuleNotFoundError` | Run `pip install -r requirements.txt` inside the activated virtual environment. |
| Port 8000 in use | Either stop the other process or use `--port 8001`. |
| No AQI data showing | In production mode, APIs may be rate-limited. System will show cached values. In demo mode, data is always available. |
