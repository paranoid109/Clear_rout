import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.neighbors import KDTree

class SpatialInterpolator:
    """
    Infers micro-level AQI for street segments based on road properties
    and proximity to official sensors, rather than simple KDTree lookup.
    """
    def __init__(self):
        self.model = RandomForestRegressor(n_estimators=50, random_state=42)
        self.is_trained = False
        self.tree = None
        self.sensor_values = None

    def train(self, sensor_data: list):
        """
        Dynamically trains the spatial model on current official sensor data.
        In a real app, this would also pull historic sensor data for the graph nodes.
        We will simulate a training step where motorways inherently read higher AQI.
        """
        if not sensor_data:
            return
            
        valid_sensors = [s for s in sensor_data if s.get('lat') and s.get('lon') and s.get('value') is not None
                         and isinstance(s.get('value'), (int, float))]
        if not valid_sensors:
            return
            
        coords = np.array([[s['lat'], s['lon']] for s in valid_sensors])
        values = np.array([s['value'] for s in valid_sensors])
        
        self.tree = KDTree(coords)
        self.sensor_values = values
        
        # Synthetic training data generation to bias the Random Forest
        # Features: [distance_to_nearest, base_sensor_value, is_motorway]
        n_samples = max(200, len(valid_sensors) * 10)
        X = []
        y = []
        
        for i in range(n_samples):
            # Pick a random sensor baseline
            idx = np.random.randint(0, len(valid_sensors))
            base_val = values[idx]
            
            # Simulate features
            dist = np.random.uniform(0, 5000) # up to 5km away
            is_motorway = 1.0 if np.random.rand() > 0.8 else 0.0
            
            # Label logic: Motorways add pollution independent of sensor.
            # Distance from sensor slightly drifts the value towards a mean (50).
            drift = (50.0 - base_val) * (dist / 5000.0)
            motorway_penalty = np.random.uniform(20.0, 50.0) if is_motorway else np.random.uniform(0.0, 5.0)
            
            label_aqi = base_val + drift + motorway_penalty
            
            X.append([dist, base_val, is_motorway])
            y.append(label_aqi)
            
        try:
            self.model.fit(X, y)
            self.is_trained = True
        except Exception as e:
            print(f"SpatialInterpolator training failed: {e}")
            self.is_trained = False

    def interpolate_edge_aqi(self, lat: float, lon: float, highway_type: str) -> float:
        """
        Predicts the AQI for a specific road edge given its center coordinates and type.
        """
        if not self.is_trained or self.tree is None:
            return 50.0 # Fallback
            
        # Find nearest sensor
        dist, ind = self.tree.query([[lat, lon]], k=1)
        dist_m = dist[0][0] * 111000 # Rough approx degrees to meters
        nearest_val = self.sensor_values[ind[0][0]]
        
        is_motorway = 1.0 if highway_type in ['motorway', 'trunk', 'primary'] else 0.0
        
        # Predict with fallback
        try:
            predicted_aqi = self.model.predict([[dist_m, nearest_val, is_motorway]])[0]
        except Exception:
            return float(nearest_val) if nearest_val else 50.0
        
        # Bound it
        return float(np.clip(predicted_aqi, 0.0, 500.0))

    def interpolate_batch(self, coords: np.ndarray, highway_types: list) -> np.ndarray:
        """
        Vectorized bulk AQI prediction for all edges at once.
        coords: Nx2 array of [lat, lon]
        highway_types: list of highway type strings
        Returns: N-length array of AQI values
        """
        n = len(coords)
        if not self.is_trained or self.tree is None or n == 0:
            return np.full(n, 50.0)
        
        # Bulk KDTree query
        dists, inds = self.tree.query(coords, k=1)
        dist_m = dists[:, 0] * 111000  # degrees to meters
        nearest_vals = self.sensor_values[inds[:, 0]]
        
        # Vectorize highway type check
        motorway_set = {'motorway', 'trunk', 'primary'}
        is_motorway = np.array([1.0 if ht in motorway_set else 0.0 for ht in highway_types])
        
        # Single batch prediction
        X = np.column_stack([dist_m, nearest_vals, is_motorway])
        try:
            predictions = self.model.predict(X)
        except Exception:
            return nearest_vals.astype(float)
        
        return np.clip(predictions, 0.0, 500.0)
