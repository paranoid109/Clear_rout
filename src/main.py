from fastapi import FastAPI, Query, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, Dict
import os
import sys
from contextlib import asynccontextmanager

# Add project root to path so 'src' module can be imported
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.api.aqi_service import AQIManager
from src.sensors.aqi_sensor import MockAQISensor
from src.fusion.fusion_engine import FusionEngine
from src.routing.basic_router import AirRouter
from src.routing.evaluator import WorthItEvaluator
from src.data.logger import AQILogger
from src.prediction.predictor import AQIPredictor

# Demo mode infrastructure
from src.demo.config import demo_config
from src.demo.middleware import DemoModeMiddleware
from src.demo.demo_logger import log_demo_startup

# Initialize shared components
aqi_manager = AQIManager()
sensor = MockAQISensor()
fusion_engine = FusionEngine()

# Lazy loading router cache with thread lock
import threading
_router_lock = threading.Lock()
routers = {}
evaluator = WorthItEvaluator()
logger = AQILogger()
predictor = AQIPredictor()

# Track initialization status
is_initializing = {}

def get_router(city: str) -> AirRouter:
    if city not in routers:
        with _router_lock:
            # Double-check after acquiring lock
            if city not in routers:
                is_initializing[city] = True
                print(f"Lazy loading router for {city}...")
                try:
                    routers[city] = AirRouter(f"data/{city}")
                finally:
                    is_initializing[city] = False
    return routers[city]

@asynccontextmanager
async def lifespan(app):
    """Run maintenance tasks on startup."""
    import asyncio
    
    if demo_config.enabled:
        # In demo mode, skip all heavy initialization (DB, ML training, graph loading).
        # The middleware will intercept all requests and return mock data.
        print("Demo Mode: Skipping heavy initialization (DB prune, ML training)...")
        await asyncio.sleep(0.5)  # Brief simulated startup
        print("Demo Mode: System ready (mock data only).")
    else:
        print("Initializing AirRoute System...")
        logger.prune_old_records(days=90)
        # Pre-train predictors
        predictor.train("amsterdam")
        predictor.train("bengaluru")
        print("System ready.")
    yield

app = FastAPI(title="AirRoute API", version="1.0.0", lifespan=lifespan)

# Attach demo mode middleware (no-op when demo_config.enabled is False)
app.add_middleware(DemoModeMiddleware, config=demo_config)
if demo_config.enabled:
    log_demo_startup(demo_config)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def read_index():
    return FileResponse('static/index.html')

class RouteResponse(BaseModel):
    user_mode: str
    route_fastest: Dict
    route_quality: Dict
    worth_it: bool
    worth_it_reason: str
    fused_aqi_baseline: float
    forecast_1h: float
    forecast_3h: float
    forecast_1w: float
    data_source: str

@app.get("/route", response_model=RouteResponse)
async def get_route(
    start_lat: float, start_lon: float,
    end_lat: float, end_lon: float,
    mode: str = Query("car", enum=["car", "bike", "walk"]),
    city: str = Query("bengaluru", enum=["amsterdam", "bengaluru"])
):
    import asyncio
    
    def _compute_route():
        """All blocking work runs in a thread pool to avoid freezing the event loop."""
        # 1. Fetch and Fuse AQI
        api_result_raw = aqi_manager.fetch_all_safe()
        raw_data = api_result_raw['data']
        data_status = api_result_raw['status']
        
        if raw_data:
            values = [d['value'] for d in raw_data if d['value'] is not None]
            api_avg = sum(values) / len(values) if values else aqi_manager.last_fused_cache
            aqi_manager._save_cache(api_avg)
        else:
            api_avg = aqi_manager.last_fused_cache
        
        sensor_val = sensor.read_aqi()
        fused_aqi = fusion_engine.fuse(sensor_val, api_avg)
        
        # 2. Log reading explicitly to the current city
        logger.log_reading(city, fused_aqi, api_avg, sensor_val)
        
        # 3. Get dual routes
        router = get_router(city)
        fastest, cleanest = router.get_dual_routes((start_lat, start_lon), (end_lat, end_lon), mode=mode, aqi_data=raw_data)
        
        # 4. Evaluate
        evaluation = evaluator.evaluate(fastest, cleanest)
        
        # 5. Predictions
        if not predictor.is_trained.get(city):
            predictor.train(city) 
        forecast_1h = predictor.predict(city, fused_aqi, 1)
        forecast_3h = predictor.predict(city, fused_aqi, 3)
        forecast_1w = predictor.predict(city, fused_aqi, 168)
        
        return {
            "user_mode": mode,
            "route_fastest": fastest,
            "route_quality": cleanest,
            "worth_it": evaluation['is_worth_it'],
            "worth_it_reason": evaluation['reason'],
            "fused_aqi_baseline": fused_aqi,
            "forecast_1h": forecast_1h,
            "forecast_3h": forecast_3h,
            "forecast_1w": forecast_1w,
            "data_source": data_status
        }

    try:
        result = await asyncio.to_thread(_compute_route)
        return result
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats")
async def get_city_stats(city: str = Query("bengaluru", enum=["amsterdam", "bengaluru"])):
    """Lightweight endpoint for city metrics without routing overhead."""
    try:
        api_result_raw = aqi_manager.fetch_all_safe()
        raw_data = api_result_raw['data']
        data_status = api_result_raw['status']
        
        if raw_data:
            values = [d['value'] for d in raw_data if d['value'] is not None]
            api_avg = sum(values) / len(values) if values else aqi_manager.last_fused_cache
        else:
            api_avg = aqi_manager.last_fused_cache
            
        sensor_val = sensor.read_aqi()
        fused_aqi = fusion_engine.fuse(sensor_val, api_avg)
        
        # Predictions
        if not predictor.is_trained.get(city):
            predictor.train(city) 
        forecast_1h = predictor.predict(city, fused_aqi, 1)
        forecast_3h = predictor.predict(city, fused_aqi, 3)
        forecast_1w = predictor.predict(city, fused_aqi, 168)
        
        return {
            "city": city,
            "fused_aqi": fused_aqi,
            "forecast_1h": forecast_1h,
            "forecast_3h": forecast_3h,
            "forecast_1w": forecast_1w,
            "data_source": data_status,
            "is_loading": is_initializing.get(city, False)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    return {
        "status": "ok", 
        "mode": "multi-city",
        "loading": is_initializing,
        "demo_mode": demo_config.enabled
    }

# ─── Demo Mode Configuration Endpoints ───────────────────────────────────────

@app.get("/demo/config")
async def get_demo_config():
    """Read the current demo mode configuration and execution stats."""
    return {
        "config": demo_config.to_dict(),
        "stats": demo_config.get_stats()
    }

@app.post("/demo/config")
async def update_demo_config(
    enabled: Optional[bool] = None,
    success_rate: Optional[float] = None,
    force_scenario: Optional[str] = None,
    min_delay_ms: Optional[int] = None,
    max_delay_ms: Optional[int] = None,
):
    """
    Update demo mode configuration at runtime.
    Only provided fields are updated; others remain unchanged.
    """
    from src.demo.demo_logger import log_config_change
    
    if enabled is not None and enabled != demo_config.enabled:
        log_config_change("enabled", demo_config.enabled, enabled)
        demo_config.enabled = enabled
        if enabled:
            log_demo_startup(demo_config)
    
    if success_rate is not None and 0.0 <= success_rate <= 1.0:
        log_config_change("success_rate", demo_config.success_rate, success_rate)
        demo_config.success_rate = success_rate
    
    if force_scenario is not None:
        # Allow "none" or empty string to clear the forced scenario
        new_val = None if force_scenario.lower() in ("", "none") else force_scenario
        log_config_change("force_scenario", demo_config.force_scenario, new_val)
        demo_config.force_scenario = new_val
    
    if min_delay_ms is not None:
        log_config_change("min_delay_ms", demo_config.min_delay_ms, min_delay_ms)
        demo_config.min_delay_ms = min_delay_ms
    
    if max_delay_ms is not None:
        log_config_change("max_delay_ms", demo_config.max_delay_ms, max_delay_ms)
        demo_config.max_delay_ms = max_delay_ms
    
    return {
        "message": "Demo config updated",
        "config": demo_config.to_dict()
    }

@app.post("/demo/reset")
async def reset_demo_stats():
    """Reset demo mode execution statistics."""
    demo_config.reset_counts()
    return {"message": "Demo stats reset", "stats": demo_config.get_stats()}

if __name__ == "__main__":
    import uvicorn
    print("\n  Open in browser: http://localhost:8000\n")
    uvicorn.run(app, host="127.0.0.1", port=8000)
