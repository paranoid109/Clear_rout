import requests
from typing import Dict, Optional
import pandas as pd
import numpy as np

class PredictionDataLoader:
    """
    Fetches external context for prediction, mainly weather from Open-Meteo.
    Also handles constructing time-series lag features.
    """
    CITY_COORDS = {
        "bengaluru": (12.9716, 77.5946),
        "amsterdam": (52.3676, 4.9041),
    }

    def __init__(self, city: str = "bengaluru"):
        coords = self.CITY_COORDS.get(city, self.CITY_COORDS["bengaluru"])
        self.lat = coords[0]
        self.lon = coords[1]
        self.weather_cache = None

    def fetch_current_weather(self) -> Dict:
        """
        Fetches current weather (temperature, wind speed, wind direction).
        Uses free Open-Meteo API.
        """
        try:
            url = f"https://api.open-meteo.com/v1/forecast?latitude={self.lat}&longitude={self.lon}&current_weather=true"
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()['current_weather']
                self.weather_cache = {
                    "temperature": data.get("temperature", 15.0),
                    "wind_speed": data.get("windspeed", 10.0),
                    "wind_direction": data.get("winddirection", 0.0)
                }
                return self.weather_cache
        except Exception as e:
            print(f"Failed to fetch weather: {e}")
            
        # Fallback defaults
        if self.weather_cache:
            return self.weather_cache
        return {"temperature": 15.0, "wind_speed": 10.0, "wind_direction": 180.0}

    def engineer_lag_features(self, df_history: pd.DataFrame) -> pd.DataFrame:
        """
        Takes a raw historical dataframe and adds structural lag features
        (e.g., AQI at T-1h, T-3h) for Gradient Boosting.
        """
        df = df_history.copy()
        df = df.sort_values(by='timestamp')
        
        # We need continuous time series for lag. 
        # Assuming df has 'fused_aqi' and is hourly.
        if 'fused_aqi' in df.columns:
            df['lag_1h'] = df['fused_aqi'].shift(1)
            df['lag_3h'] = df['fused_aqi'].shift(3)
            
            # Simple synthetic mock for weather and traffic historicals if missing
            if 'wind_speed' not in df.columns:
                df['wind_speed'] = np.random.uniform(5, 25, len(df))
            if 'temperature' not in df.columns:
                df['temperature'] = np.random.uniform(5, 25, len(df))
            if 'traffic_index' not in df.columns:
                # Add congestion based on hour
                hours = pd.to_datetime(df['timestamp']).dt.hour
                traffic = np.where((hours >= 7) & (hours <= 9), 0.8, 0.2)
                traffic = np.where((hours >= 16) & (hours <= 19), 0.9, traffic)
                df['traffic_index'] = traffic + np.random.uniform(-0.1, 0.1, len(df))
                
            # Fill NAs from shifting
            df.bfill(inplace=True)
            df.ffill(inplace=True)
            
        return df

if __name__ == "__main__":
    loader = PredictionDataLoader()
    print("Current Weather:", loader.fetch_current_weather())
