import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler

class MinuteVentilationModel:
    """
    Predicts physiological Minute Ventilation (V_E) in Liters/min 
    based on transport mode, speed, and incline.
    """
    def __init__(self):
        self.model = RandomForestRegressor(n_estimators=50, random_state=42)
        self.scaler = StandardScaler()
        self.is_trained = False
        self._train_synthetic_baseline()

    def _train_synthetic_baseline(self):
        """
        Trains the regression model on a synthetic physiological baseline dataset.
        V_E is highly dependent on power output (speed & incline).
        """
        np.random.seed(42)
        n_samples = 2000
        
        # Modes: 0=car (driver passenger), 1=bike, 2=walk
        modes = np.random.choice([0, 1, 2], size=n_samples)
        speeds = np.zeros(n_samples)
        inclines = np.random.uniform(-5.0, 15.0, size=n_samples)
        v_e = np.zeros(n_samples)
        
        for i in range(n_samples):
            m = modes[i]
            inc = inclines[i]
            if m == 0:  # Car (Sedentary)
                speeds[i] = np.random.uniform(0.0, 100.0)
                v_e[i] = np.random.normal(7.0, 1.0) # V_E resting is ~6-8 L/min
            elif m == 1: # Bike
                speeds[i] = np.random.uniform(5.0, 30.0)
                base_ve = 20.0 + (speeds[i] - 15.0) * 1.5
                incline_factor = np.maximum(0, inc) * 3.0 # Big penalty for uphill
                v_e[i] = base_ve + incline_factor + np.random.normal(0, 3.0)
            elif m == 2: # Walk
                speeds[i] = np.random.uniform(2.0, 7.0)
                base_ve = 12.0 + (speeds[i] - 4.0) * 2.5
                incline_factor = np.maximum(0, inc) * 1.5
                v_e[i] = base_ve + incline_factor + np.random.normal(0, 1.5)
                
        # Ensure minimum V_E
        v_e = np.maximum(v_e, 6.0)
        
        X = np.column_stack((modes, speeds, inclines))
        y = v_e
        
        X_scaled = self.scaler.fit_transform(X)
        self.model.fit(X_scaled, y)
        self.is_trained = True
        
    def predict_ve(self, mode_str: str, speed_kmh: float, incline_pct: float) -> float:
        """
        Predicts V_E in L/min.
        """
        mode_map = {"car": 0, "bike": 1, "walk": 2, "drive": 0}
        mode_idx = mode_map.get(mode_str.lower(), 0)
        
        X_test = np.array([[mode_idx, speed_kmh, incline_pct]])
        X_scaled = self.scaler.transform(X_test)
        
        return float(self.model.predict(X_scaled)[0])

    def calculate_pm25_inhaled(self, aqi: float, ve_l_min: float, duration_min: float) -> float:
        """
        Translates AQI/Concentration into physical PM2.5 inhaled (micrograms).
        Roughly: AQI 50 ~= 12 ug/m^3 PM2.5.
        Formula: Concentration (ug/L) * Ve (L/min) * Time (min)
        """
        # Linear approximation for PM2.5 concentration from AQI (simplification for model)
        # 1 m^3 = 1000 L
        if aqi <= 50:
            pm25_concentration_ug_m3 = (12.0 / 50.0) * aqi
        elif aqi <= 100:
            pm25_concentration_ug_m3 = ((35.4 - 12.1) / 50.0) * (aqi - 50) + 12.1
        else:
            pm25_concentration_ug_m3 = ((55.4 - 35.5) / 50.0) * (aqi - 100) + 35.5
            
        concentration_ug_L = pm25_concentration_ug_m3 / 1000.0
        
        total_inhaled_ug = concentration_ug_L * ve_l_min * duration_min
        return total_inhaled_ug

if __name__ == "__main__":
    model = MinuteVentilationModel()
    print("V_E (Drive flat 40kmh):", model.predict_ve("car", 40.0, 0.0))
    print("V_E (Walk flat 5kmh):", model.predict_ve("walk", 5.0, 0.0))
    print("V_E (Walk uphill 5kmh 10%):", model.predict_ve("walk", 5.0, 10.0))
    print("V_E (Bike flat 20kmh):", model.predict_ve("bike", 20.0, 0.0))
    print("V_E (Bike uphill 20kmh 10%):", model.predict_ve("bike", 20.0, 10.0))
