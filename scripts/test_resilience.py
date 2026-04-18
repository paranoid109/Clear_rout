import sys
import os
from unittest.mock import patch

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.api.aqi_service import AQIManager
from src.fusion.fusion_engine import FusionEngine

def test_chaos_scenarios():
    print("--- AirRoute Phase 4: Chaos Mode Resilience Testing ---")
    
    manager = AQIManager()
    fusion = FusionEngine()
    results = []
    
    # Scenario 1: API Partial Outage (Luchtmeetnet down, others up)
    print("\n[Scenario 1] Luchtmeetnet Down, Others Up")
    with patch('src.api.aqi_service.LuchtmeetnetClient.get_measurements', return_value=[]):
        result = manager.get_average_aqi()
        print(f"Status: {result['status']} | Value: {result['value']}")
        passed = result['status'] == "DEGRADED"
        print(f"{'SUCCESS' if passed else 'FAIL'}: System {'recognized' if passed else 'did not recognize'} partial API failure.")
        results.append(("Partial Outage", passed))
    
    # Scenario 2: Total API Outage (All 4 APIs down)
    print("\n[Scenario 2] Total API Outage")
    with patch('src.api.aqi_service.LuchtmeetnetClient.get_measurements', return_value=[]), \
         patch('src.api.aqi_service.OpenAQv3Client.get_measurements', return_value=[]), \
         patch('src.api.aqi_service.WAQIClient.get_measurements', return_value=[]), \
         patch('src.api.aqi_service.IQAirClient.get_measurements', return_value=[]):
        result = manager.get_average_aqi()
        print(f"Status: {result['status']} | Value: {result['value']} (from cache)")
        passed = result['status'] == "CACHE_ONLY"
        print(f"{'SUCCESS' if passed else 'FAIL'}: System {'fell back to cache' if passed else 'did not fall back to cache'}.")
        results.append(("Total API Outage", passed))

    # Scenario 3: Sensor Failure
    print("\n[Scenario 3] Sensor Disconnected")
    sensor_val = None
    api_val = 50.0
    fused = fusion.fuse(sensor_val, api_val)
    print(f"Fused Value (Sensor=None): {fused}")
    passed = fused == api_val
    print(f"{'SUCCESS' if passed else 'FAIL'}: Fusion engine {'fell back to API-only' if passed else 'did not fall back correctly'}.")
    results.append(("Sensor Failure", passed))

    # Scenario 4: Total System Blackout (All APIs + Sensor down)
    print("\n[Scenario 4] Total Blackout")
    with patch('src.api.aqi_service.LuchtmeetnetClient.get_measurements', return_value=[]), \
         patch('src.api.aqi_service.OpenAQv3Client.get_measurements', return_value=[]), \
         patch('src.api.aqi_service.WAQIClient.get_measurements', return_value=[]), \
         patch('src.api.aqi_service.IQAirClient.get_measurements', return_value=[]):
        result = manager.get_average_aqi()
        # Also verify fusion falls back when sensor is None
        fused = fusion.fuse(None, None)
        print(f"API Status: {result['status']} | Cached Value: {result['value']}")
        print(f"Fusion fallback (both None): {fused}")
        api_passed = result['status'] == "CACHE_ONLY"
        fusion_passed = fused == 50.0  # safe default
        passed = api_passed and fusion_passed
        print(f"{'SUCCESS' if passed else 'FAIL'}: System {'served last known good cache + fusion default' if passed else 'did not handle total blackout correctly'}.")
        results.append(("Total Blackout", passed))

    # Summary
    print("\n" + "=" * 50)
    print("RESILIENCE TEST SUMMARY")
    print("=" * 50)
    total = len(results)
    passed_count = sum(1 for _, p in results if p)
    for name, passed in results:
        print(f"  {'PASS' if passed else 'FAIL'} | {name}")
    print(f"\nResult: {passed_count}/{total} scenarios passed.")
    if passed_count == total:
        print("All resilience tests PASSED.")
    else:
        print("Some resilience tests FAILED.")
    print()

if __name__ == "__main__":
    test_chaos_scenarios()
