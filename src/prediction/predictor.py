import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from src.prediction.data_loader import PredictionDataLoader

class AQIPredictor:
    """
    Spatiotemporal forecasting engine for AQI using Gradient Boosting.
    Leverages lag features and current weather.
    """
    def __init__(self, db_path="data/air_quality_history.db"):
        self.db_path = db_path
        self.models = {}
        self.is_trained = {}
        self.data_loaders = {}

    def _get_data_loader(self, city: str) -> PredictionDataLoader:
        """Returns a city-specific data loader, creating one if needed."""
        if city not in self.data_loaders:
            self.data_loaders[city] = PredictionDataLoader(city=city)
        return self.data_loaders[city]

    def train(self, city="bengaluru"):
        """Trains the model on historical data from SQLite for a specific city."""
        if not os.path.exists(self.db_path):
            return

        with sqlite3.connect(self.db_path) as conn:
            df = pd.read_sql_query("SELECT timestamp, fused_aqi FROM measurements WHERE city=?", conn, params=[city])
        
        if len(df) < 24:
            print(f"Not enough data to train model for {city}.")
            self.is_trained[city] = False
            return

        # Feature Engineering for lag and weather via dataloader
        data_loader = self._get_data_loader(city)
        df = data_loader.engineer_lag_features(df)
        
        df['hour'] = pd.to_datetime(df['timestamp']).dt.hour
        df['dayofweek'] = pd.to_datetime(df['timestamp']).dt.dayofweek
        
        # Features: hour, dow, lag_1h, lag_3h, wind_speed, temp, traffic
        features = ['hour', 'dayofweek', 'lag_1h', 'lag_3h', 'wind_speed', 'temperature', 'traffic_index']
        X = df[features].values
        y = df['fused_aqi'].values
        
        # Simple evaluation
        split_idx = int(len(df) * 0.8)
        X_train, X_test = X[:split_idx], X[split_idx:]
        y_train, y_test = y[:split_idx], y[split_idx:]
        
        # Gradient Boosting as high-performance alternative to LSTM/XGBoost for tabular data
        model = GradientBoostingRegressor(n_estimators=150, learning_rate=0.1, random_state=42)
        model.fit(X_train, y_train)
        
        # Calculate MAE to show predictability
        preds = model.predict(X_test)
        mae = mean_absolute_error(y_test, preds)
        print(f"Gradient Boosting predictor trained | MAE: {mae:.2f} AQI")
        
        # Retrain on full data for best real-time performance
        model.fit(X, y)
        self.models[city] = model
        self.is_trained[city] = True

    def predict(self, city: str, current_aqi: float, horizon_hours: int) -> float:
        """
        Predicts future AQI. If model missing, falls back to persistence.
        """
        if not self.is_trained.get(city, False):
            return current_aqi

        target_time = datetime.now() + timedelta(hours=horizon_hours)
        target_hour = target_time.hour
        target_dow = target_time.weekday()
        
        # Current conditions
        data_loader = self._get_data_loader(city)
        weather = data_loader.fetch_current_weather()
        wind_speed = weather.get("wind_speed", 10.0)
        temp = weather.get("temperature", 15.0)
        
        # Simplistic traffic estimation logic
        traffic = 0.8 if target_hour in [7, 8, 9, 16, 17, 18] else 0.3
        
        # Features array
        # ['hour', 'dayofweek', 'lag_1h', 'lag_3h', 'wind_speed', 'temperature', 'traffic_index']
        # Since we are predicting the future, lag_1h and lag_3h are effectively just the current_aqi
        # (A full auto-regressive step out would be more complex, we simplify for embedded realtime)
        lag_1h = current_aqi
        lag_3h = current_aqi * 0.95 # Slight decay assumption
        
        prediction = self.models[city].predict([[
            target_hour, target_dow, lag_1h, lag_3h, wind_speed, temp, traffic
        ]])[0]
        
        # Heavy dampening of current AQI for long horizons
        weight = max(0.0, 1.0 - (horizon_hours / 24.0))
        final_prediction = (weight * current_aqi) + ((1 - weight) * prediction)
        
        return float(final_prediction)

if __name__ == "__main__":
    predictor = AQIPredictor()
    predictor.train("bengaluru")
    if predictor.is_trained.get("bengaluru"):
         print(f"7-day Forecast (+168h): {predictor.predict('bengaluru', 50.0, 168)}")
