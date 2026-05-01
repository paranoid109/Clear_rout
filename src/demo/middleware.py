"""
Demo Mode Middleware
--------------------
FastAPI middleware that intercepts API requests when demo mode is enabled.
Completely transparent (zero overhead) when demo mode is disabled.
"""
import asyncio
import random
import json
from urllib.parse import urlparse, parse_qs

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from src.demo.config import DemoConfig, demo_config
from src.demo.scenarios import ScenarioSelector, TIMEOUT, get_scenario_description
from src.demo import demo_logger


# Endpoints that the demo middleware intercepts
_INTERCEPTED_ENDPOINTS = {"/route", "/stats", "/health"}


class DemoModeMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for demo mode edge-case simulation.
    
    When demo_config.enabled is True:
        - Intercepts requests to /route, /stats, /health
        - Selects a scenario (success, error, timeout, etc.)
        - Applies simulated latency
        - Returns mock data instead of calling real backend
        - Logs the scenario to console
        
    When demo_config.enabled is False:
        - Complete pass-through. Zero overhead. No interception.
    """
    
    def __init__(self, app, config: DemoConfig = None):
        super().__init__(app)
        self.config = config or demo_config
        self.selector = ScenarioSelector(self.config)
    
    async def dispatch(self, request: Request, call_next):
        # Fast exit: if demo mode is off, pass through immediately
        if not self.config.enabled:
            return await call_next(request)
        
        # Only intercept specific API endpoints
        path = request.url.path
        if path not in _INTERCEPTED_ENDPOINTS:
            return await call_next(request)
        
        # Extract query parameters for context
        query_params = dict(request.query_params)
        mode = query_params.get("mode", "car")
        city = query_params.get("city", "bengaluru")
        demo_force = query_params.get("demo_force", None)
        
        # Extract coordinates for routing realism
        coords = None
        if path == "/route":
            try:
                coords = {
                    "start_lat": float(query_params.get("start_lat", 0)),
                    "start_lon": float(query_params.get("start_lon", 0)),
                    "end_lat": float(query_params.get("end_lat", 0)),
                    "end_lon": float(query_params.get("end_lon", 0)),
                }
            except (ValueError, TypeError):
                pass
        
        # Select scenario
        scenario = self.selector.select(endpoint=path, query_force=demo_force)
        
        # Record execution
        self.config.record_scenario(scenario)
        
        # Calculate simulated delay
        delay_ms = random.randint(self.config.min_delay_ms, self.config.max_delay_ms)
        
        # For timeout scenarios, use the configured timeout duration
        if scenario == TIMEOUT:
            delay_ms = int(self.config.timeout_duration_s * 1000)
        
        # Log the scenario
        if self.config.log_scenarios:
            description = get_scenario_description(scenario)
            demo_logger.log_scenario(scenario, path, delay_ms, description)
        
        # Apply simulated delay
        await asyncio.sleep(delay_ms / 1000.0)
        
        # Generate response
        status_code, body = self.selector.get_response_data(
            scenario=scenario,
            endpoint=path,
            mode=mode,
            city=city,
            coords=coords
        )
        
        if body is None:
            # No mock data for this endpoint — pass through to real handler
            return await call_next(request)
        
        # Add demo metadata header
        response = JSONResponse(content=body, status_code=status_code)
        response.headers["X-AirRoute-Demo"] = "true"
        response.headers["X-AirRoute-Demo-Scenario"] = scenario
        response.headers["X-AirRoute-Demo-Delay-Ms"] = str(delay_ms)
        
        return response
