from typing import Optional

class FusionEngine:
    def __init__(self, w_sensor: float = 0.6, w_api: float = 0.4):
        self.w_sensor = w_sensor
        self.w_api = w_api

    def fuse(self, sensor_val: Optional[float], api_val: Optional[float]) -> float:
        """
        Blends sensor and API values based on SOP weights.
        Handles fallback cases where one or both inputs are missing.
        """
        # If both are available, use weighted blend
        if sensor_val is not None and api_val is not None:
            return (self.w_sensor * sensor_val) + (self.w_api * api_val)
        
        # Fallback to sensor if API is missing
        if sensor_val is not None:
            return sensor_val
        
        # Fallback to API if sensor is missing
        if api_val is not None:
            return api_val
        
        # Safe default if everything fails
        return 50.0

if __name__ == "__main__":
    engine = FusionEngine()
    print(f"Fused (S: 60, A: 40): {engine.fuse(60, 40)}")
    print(f"Fused (S: None, A: 40): {engine.fuse(None, 40)}")
    print(f"Fused (S: 60, A: None): {engine.fuse(60, None)}")
