import sys
import os
import json

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.routing.basic_router import AirRouter
from src.routing.evaluator import WorthItEvaluator
from src.fusion.fusion_engine import FusionEngine
from src.api.aqi_service import AQIManager
from src.sensors.aqi_sensor import MockAQISensor
from src.data.logger import AQILogger
from src.prediction.predictor import AQIPredictor

def verify_system():
    print("=== AirRoute Phase 3 System Verification ===")
    
    # Coordinates: Dam Square to Rijksmuseum
    loc_a = (52.3731, 4.8926)
    loc_b = (52.3600, 4.8852)
    
    # 1. Check Graphs
    modes = ["drive", "bike", "walk"]
    base_path = "data/amsterdam"
    for mode in modes:
        path = f"{base_path}_{mode}.graphml"
        if not os.path.exists(path):
            print(f"Graph missing: {path}. Please run download_graph.py first.")
            # We'll continue but this will likely fail later if the file isn't there
    
    # 2. Initialize Components
    try:
        router = AirRouter(base_path)
        evaluator = WorthItEvaluator()
        fusion = FusionEngine()
        logger = AQILogger()
        predictor = AQIPredictor()
        aqi_mgr = AQIManager()
        sensor = MockAQISensor()
        
        print("\n[Testing Multi-Mode Routing]")
        for user_mode in ["car", "bike", "walk"]:
            print(f"\n--- Mode: {user_mode} ---")
            
            # Fetch data
            api_result = aqi_mgr.get_average_aqi()
            api_val = api_result['value']
            sensor_val = sensor.read_aqi()
            fused = fusion.fuse(sensor_val, api_val)
            print(f"Fused AQI: {fused:.1f}")
            
            # Log
            logger.log_reading('amsterdam', fused, api_val, sensor_val)
            
            # Route
            fast, clean = router.get_dual_routes(loc_a, loc_b, mode=user_mode)
            print(f"Fastest: {fast['time_min']:.2f} min | AQI: {fast['aqi_mean']:.1f}")
            print(f"Cleanest: {clean['time_min']:.2f} min | AQI: {clean['aqi_mean']:.1f}")
            
            # Evaluate
            result = evaluator.evaluate(fast, clean)
            print(f"Worth it? {result['is_worth_it']} | Reason: {result['reason']}")
            
            # Prediction (Mock training for first run)
            predictor.train('amsterdam')
            p1h = predictor.predict('amsterdam', fused, 1)
            print(f"Prediction (+1h): {p1h:.1f}")
            
        print("\nVerification Complete.")
        
    except Exception as e:
        print(f"\nVerification Failed: {e}")

if __name__ == "__main__":
    verify_system()
