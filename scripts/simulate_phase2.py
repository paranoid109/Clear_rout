import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.api.aqi_service import AQIManager
from src.sensors.aqi_sensor import MockAQISensor
from src.fusion.fusion_engine import FusionEngine
from src.routing.basic_router import AirRouter
from src.routing.evaluator import WorthItEvaluator

def run_simulation():
    print("--- AirRoute Phase 2 Simulation ---")
    
    # 1. Initialize Modules
    aqi_manager = AQIManager()
    sensor = MockAQISensor()
    fusion_engine = FusionEngine()
    evaluator = WorthItEvaluator()
    
    graph_path = "data/amsterdam"
    if not os.path.exists(f"{graph_path}_drive.graphml"):
        print("Error: Graph not found. Run download_graph.py first.")
        return
    
    router = AirRouter(graph_path)
    
    # 2. Data Acquisition
    print("\n[Data Acquisition]")
    try:
        api_result = aqi_manager.get_average_aqi()
        api_avg = api_result['value']
        print(f"API Mean AQI: {api_avg:.2f} (Status: {api_result['status']})")
    except Exception:
        api_avg = 40.0
        print("Warning: API fetch failed, using default.")
        
    sensor_val = sensor.read_aqi()
    print(f"Hyperlocal Sensor AQI: {sensor_val:.2f}")
    
    # 3. Fusion
    print("\n[Fusion Engine]")
    fused_aqi = fusion_engine.fuse(sensor_val, api_avg)
    print(f"Final Fused AQI: {fused_aqi:.2f}")
    
    # 4. Routing
    print("\n[Routing Engine]")
    # Dam Square to Rijksmuseum
    start_coords = (52.3731, 4.8926)
    end_coords = (52.3600, 4.8852)
    
    # get_dual_routes calls update_aqi_on_graph internally
    fastest, cleanest = router.get_dual_routes(start_coords, end_coords)
    
    print(f"Fastest Route: {fastest['time_min']:.2f} min | Mean AQI: {fastest['aqi_mean']:.1f}")
    print(f"Cleanest Route: {cleanest['time_min']:.2f} min | Mean AQI: {cleanest['aqi_mean']:.1f}")
    
    # 5. Evaluation
    print("\n[Evaluator]")
    evaluation = evaluator.evaluate(fastest, cleanest)
    print(f"Result: {evaluation['reason']}")
    
    # 6. Final Output (JSON format)
    import json
    final_output = {
        "user_mode": "car",
        "route_fastest": {"time_min": fastest['time_min'], "aqi_mean": fastest['aqi_mean']},
        "route_quality": {"time_min": cleanest['time_min'], "aqi_mean": cleanest['aqi_mean']},
        "worth_it": evaluation['is_worth_it'],
        "worth_it_reason": evaluation['reason'],
        "fused_aqi_baseline": fused_aqi
    }
    
    print("\nFinal API Response Snapshot:")
    print(json.dumps(final_output, indent=2))

if __name__ == "__main__":
    run_simulation()

