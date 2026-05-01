"""Quick test to verify the demo module imports and generators work."""
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.demo.config import demo_config
from src.demo.scenarios import ScenarioSelector
from src.demo.mock_data import (
    generate_route_success, generate_stats_success,
    generate_empty_route_response, generate_partial_route_response,
    generate_error_detail
)
from src.demo.demo_logger import log_scenario

print("=== Demo Module Import Test ===\n")

# 1. Config
print(f"Config: enabled={demo_config.enabled}, success_rate={demo_config.success_rate}")

# 2. Scenario selection
selector = ScenarioSelector(demo_config)
for i in range(5):
    s = selector.select("/route")
    print(f"  Scenario roll #{i+1}: {s}")

# 3. Mock data — Success
print("\n--- Mock Route (Success with Coords) ---")
coords = {"start_lat": 12.97, "start_lon": 77.59, "end_lat": 12.98, "end_lon": 77.60}
r = generate_route_success("car", "bengaluru", coords)
print(f"  Mode: {r['user_mode']}")
print(f"  Path length: {len(r['route_fastest']['path'])} points")
print(f"  Starts at: {r['route_fastest']['path'][0]}")
print(f"  Ends at: {r['route_fastest']['path'][-1]}")
print(f"  Fastest: {r['route_fastest']['time_min']:.1f} min, AQI={r['route_fastest']['aqi_mean']}")
print(f"  Worth it: {r['worth_it']} — {r['worth_it_reason']}")

# 4. Mock data — Empty
print("\n--- Mock Route (Empty) ---")
e = generate_empty_route_response("bike")
print(f"  Path length: {len(e['route_fastest']['path'])}")
print(f"  Worth it: {e['worth_it']}")

# 5. Mock data — Partial
print("\n--- Mock Route (Partial) ---")
p = generate_partial_route_response("walk", "amsterdam")
print(f"  Has forecast_1w: {'forecast_1w' in p and p['forecast_1w'] is not None}")
print(f"  Data source: {p['data_source']}")

# 6. Error detail
print(f"\n--- Error Detail ---")
print(f"  {generate_error_detail()}")

# 7. Logger test
print("\n--- Logger Test ---")
log_scenario("SUCCESS", "/route", 150, "Normal successful response")
log_scenario("API_ERROR", "/stats", 80, "Simulated 500 Internal Server Error")
log_scenario("TIMEOUT", "/route", 5000, "Simulated Gateway Timeout")

# 8. Stats
print("\n--- Mock Stats ---")
s = generate_stats_success("amsterdam")
print(f"  City: {s['city']}, AQI: {s['fused_aqi']}, Source: {s['data_source']}")

print("\n[OK] All demo module tests PASSED!")
