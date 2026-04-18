"""
Mock Data Generators
--------------------
Produces realistic, varied mock data for all AirRoute endpoints.
Every call generates unique IDs, timestamps, and values — never returns
identical responses twice.
"""
import random
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional


def _rand_aqi() -> float:
    """Generate a realistic AQI value with urban distribution bias."""
    # Most cities range 20-120; occasionally spike higher
    if random.random() < 0.1:
        return round(random.uniform(150, 300), 1)  # Pollution spike
    return round(random.uniform(25, 120), 1)


# Road-aligned path skeletons for realistic demo routes
_ROAD_PATHS = {
    "bengaluru": [
        # MG Road to Indiranagar
        [[12.9733, 77.5995], [12.9738, 77.6053], [12.9742, 77.6124], [12.9770, 77.6200], [12.9785, 77.6320], [12.9750, 77.6410], [12.9720, 77.6435]],
        # Koramangala to HSR Layout
        [[12.9352, 77.6180], [12.9300, 77.6200], [12.9250, 77.6250], [12.9200, 77.6300], [12.9150, 77.6350], [12.9100, 77.6400], [12.9050, 77.6450]],
        # Whitefield to Marathahalli
        [[12.9698, 77.7500], [12.9680, 77.7400], [12.9650, 77.7300], [12.9620, 77.7150], [12.9591, 77.7000]]
    ],
    "amsterdam": [
        # Dam Square to Centraal
        [[52.3731, 4.8926], [52.3735, 4.8931], [52.3745, 4.8940], [52.3755, 4.8950], [52.3765, 4.8960], [52.3775, 4.8970], [52.3785, 4.8980], [52.3791, 4.8988]],
        # Rijksmuseum to Vondelpark
        [[52.3600, 4.8852], [52.3610, 4.8820], [52.3620, 4.8780], [52.3615, 4.8740], [52.3600, 4.8700]],
        # Anne Frank House to Westergasfabriek
        [[52.3752, 4.8840], [52.3780, 4.8800], [52.3810, 4.8770], [52.3835, 4.8730], [52.3850, 4.8700]]
    ]
}


def _rand_coords(city: str = "bengaluru") -> List[List[float]]:
    """Generate a realistic, road-aligned polyline path for the given city."""
    # Pick a random skeleton path for the city
    skeletons = _ROAD_PATHS.get(city.lower(), _ROAD_PATHS["bengaluru"])
    skeleton = random.choice(skeletons)
    
    # Optionally jitter the whole path slightly so it's not identical every time
    lat_off = random.uniform(-0.001, 0.001)
    lon_off = random.uniform(-0.001, 0.001)
    
    path = []
    for lat, lon in skeleton:
        path.append([round(lat + lat_off, 6), round(lon + lon_off, 6)])
        
    # If we need more points, we could interpolate, but the skeletons are usually enough
    return path


def _rand_route(city: str = "bengaluru", bias: str = "neutral") -> Dict:
    """
    Generate a single route result with realistic metrics.
    
    bias: "fast" for shorter time / higher AQI,
          "clean" for longer time / lower AQI,
          "neutral" for balanced
    """
    base_time = random.uniform(5, 35)  # minutes
    base_aqi = _rand_aqi()
    
    if bias == "fast":
        time_min = round(base_time * random.uniform(0.7, 0.9), 2)
        aqi_mean = round(base_aqi * random.uniform(1.1, 1.4), 1)
    elif bias == "clean":
        time_min = round(base_time * random.uniform(1.05, 1.3), 2)
        aqi_mean = round(base_aqi * random.uniform(0.5, 0.8), 1)
    else:
        time_min = round(base_time, 2)
        aqi_mean = round(base_aqi, 1)
    
    distance_km = round(time_min * random.uniform(0.3, 0.8), 2)
    exposure = round(aqi_mean * time_min, 1)
    pm25 = round(random.uniform(2, 50), 2)
    
    path = _rand_coords(city)
    
    return {
        "route": list(range(len(path))),
        "distance_km": distance_km,
        "time_min": time_min,
        "aqi_mean": aqi_mean,
        "exposure_index": exposure,
        "pm25_inhaled_ug": pm25,
        "nodes": list(range(len(path))),
        "path": path,
        "is_fallback": False,
    }


def generate_route_success(mode: str = "car", city: str = "bengaluru") -> Dict:
    """Generate a complete, realistic success response for /route."""
    fastest = _rand_route(city, bias="fast")
    cleanest = _rand_route(city, bias="clean")
    
    pm25_diff = fastest["pm25_inhaled_ug"] - cleanest["pm25_inhaled_ug"]
    cigs = pm25_diff / 22.0
    time_diff = cleanest["time_min"] - fastest["time_min"]
    
    worth_it = pm25_diff >= 2.0 and time_diff <= 10.0
    
    if worth_it and cigs >= 0.05:
        reason = f"Taking this route saves you from inhaling the equivalent of {cigs:.1f} cigarettes worth of smog."
    elif worth_it:
        reason = f"Taking the air-quality route saves {pm25_diff:.1f} ug of PM2.5 at a cost of {time_diff:.1f} min extra travel. Recommended."
    elif pm25_diff < 2.0:
        reason = "The air quality improvement is negligible on this route."
    else:
        reason = f"The time penalty ({time_diff:.1f} min) is too high for the exposure savings."
    
    fused = round(random.uniform(30, 90), 1)
    
    return {
        "user_mode": mode,
        "route_fastest": fastest,
        "route_quality": cleanest,
        "worth_it": worth_it,
        "worth_it_reason": reason,
        "fused_aqi_baseline": fused,
        "forecast_1h": round(fused + random.uniform(-5, 8), 1),
        "forecast_3h": round(fused + random.uniform(-10, 15), 1),
        "forecast_1w": round(fused + random.uniform(-20, 25), 1),
        "data_source": random.choice(["API_FULL", "DEGRADED"]),
    }


def generate_stats_success(city: str = "bengaluru") -> Dict:
    """Generate a complete success response for /stats."""
    fused = round(random.uniform(25, 100), 1)
    return {
        "city": city,
        "fused_aqi": fused,
        "forecast_1h": round(fused + random.uniform(-5, 8), 1),
        "forecast_3h": round(fused + random.uniform(-10, 15), 1),
        "forecast_1w": round(fused + random.uniform(-20, 25), 1),
        "data_source": random.choice(["API_FULL", "DEGRADED"]),
        "is_loading": False,
    }


def generate_empty_route_response(mode: str = "car") -> Dict:
    """Generate a valid-schema response with empty/zero data (no route found)."""
    return {
        "user_mode": mode,
        "route_fastest": {
            "route": [],
            "distance_km": 0.0,
            "time_min": 0.0,
            "aqi_mean": 0.0,
            "exposure_index": 0.0,
            "pm25_inhaled_ug": 0.0,
            "nodes": [],
            "path": [],
            "is_fallback": True,
            "error_message": "Demo Mode: No route data available (empty response simulation)",
        },
        "route_quality": {
            "route": [],
            "distance_km": 0.0,
            "time_min": 0.0,
            "aqi_mean": 0.0,
            "exposure_index": 0.0,
            "pm25_inhaled_ug": 0.0,
            "nodes": [],
            "path": [],
            "is_fallback": True,
            "error_message": "Demo Mode: No route data available (empty response simulation)",
        },
        "worth_it": False,
        "worth_it_reason": "No route data available.",
        "fused_aqi_baseline": 0.0,
        "forecast_1h": 0.0,
        "forecast_3h": 0.0,
        "forecast_1w": 0.0,
        "data_source": "CACHE_ONLY",
    }


def generate_empty_stats_response(city: str = "bengaluru") -> Dict:
    """Generate a valid-schema stats response with no data."""
    return {
        "city": city,
        "fused_aqi": 0.0,
        "forecast_1h": 0.0,
        "forecast_3h": 0.0,
        "forecast_1w": 0.0,
        "data_source": "CACHE_ONLY",
        "is_loading": False,
    }


def generate_partial_route_response(mode: str = "car", city: str = "bengaluru") -> Dict:
    """
    Generate a response with some fields missing or incomplete.
    Simulates real-world partial data scenarios.
    """
    response = generate_route_success(mode, city)
    
    # Randomly remove optional fields
    partial_choices = [
        lambda r: r["route_quality"].pop("pm25_inhaled_ug", None),
        lambda r: r.update({"forecast_1w": None}),
        lambda r: r["route_fastest"].update({"path": r["route_fastest"]["path"][:2]}),  # Truncated path
        lambda r: r.update({"worth_it_reason": ""}),
        lambda r: r["route_quality"].update({"exposure_index": None}),
    ]
    
    # Apply 1-3 random partial removals
    num_partials = random.randint(1, 3)
    for fn in random.sample(partial_choices, min(num_partials, len(partial_choices))):
        fn(response)
    
    response["data_source"] = "DEGRADED"
    return response


def generate_partial_stats_response(city: str = "bengaluru") -> Dict:
    """Generate a stats response with some missing forecast fields."""
    response = generate_stats_success(city)
    
    if random.random() > 0.5:
        response["forecast_1w"] = None
    if random.random() > 0.7:
        response["forecast_3h"] = None
    
    response["data_source"] = "DEGRADED"
    return response


def generate_error_detail() -> str:
    """Generate a realistic error message for API failure simulation."""
    errors = [
        "Simulated 500 Internal Server Error: AQI data pipeline unreachable",
        "Simulated 503 Service Unavailable: All upstream API providers timed out",
        "Simulated 502 Bad Gateway: Routing engine process crashed",
        "Simulated database connection pool exhausted",
        "Simulated OSMnx graph loading MemoryError",
        "Simulated network partition: Unable to reach air quality data sources",
    ]
    return random.choice(errors)


def generate_validation_error_detail() -> Dict:
    """Generate a realistic validation error."""
    errors = [
        {"field": "start_lat", "message": "Latitude must be between -90 and 90", "value": 999.0},
        {"field": "end_lon", "message": "Longitude must be between -180 and 180", "value": -200.5},
        {"field": "mode", "message": "Invalid transport mode. Must be 'car', 'bike', or 'walk'", "value": "helicopter"},
        {"field": "city", "message": "City 'tokyo' is not supported. Available: bengaluru, amsterdam", "value": "tokyo"},
        {"field": "coordinates", "message": "Start and end points are identical", "value": "(12.97, 77.59)"},
    ]
    return random.choice(errors)
