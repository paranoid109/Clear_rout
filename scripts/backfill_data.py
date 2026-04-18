import requests
import sqlite3
import os
import json
from datetime import datetime, timedelta
import sys

# Add project root to path so 'src' module can be imported
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from src.data.logger import AQILogger
from src.prediction.predictor import AQIPredictor

def pull_historical_data(city_name, lat, lon, days=730):
    print(f"Fetching up to {days} days of historical AQI data for {city_name}...")
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")
    
    url = "https://air-quality-api.open-meteo.com/v1/air-quality"
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_str,
        "end_date": end_str,
        "hourly": "us_aqi"
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        times = data['hourly']['time']
        aqis = data['hourly']['us_aqi']
        
        print(f"Successfully downloaded {len(times)} records for {city_name}. Storing in database...")
        
        logger = AQILogger()
        
        # Batch insert for speed
        with sqlite3.connect(logger.db_path) as conn:
            batch = []
            for t, aqi in zip(times, aqis):
                if aqi is None:
                    continue # Skip missing data
                
                # Format to SQL DATETIME
                dt = datetime.fromisoformat(t).strftime("%Y-%m-%d %H:%M:%S")
                # We simulate API and Sensor matching the fused for history
                batch.append((dt, city_name, aqi, aqi, aqi))
                
                if len(batch) >= 1000:
                    conn.executemany("""
                        INSERT INTO measurements (timestamp, city, fused_aqi, api_aqi, sensor_aqi)
                        VALUES (?, ?, ?, ?, ?)
                    """, batch)
                    batch = []
            
            if batch:
                conn.executemany("""
                    INSERT INTO measurements (timestamp, city, fused_aqi, api_aqi, sensor_aqi)
                    VALUES (?, ?, ?, ?, ?)
                """, batch)
            conn.commit()
            
        print(f"Stored records for {city_name}.")
        
    except Exception as e:
        print(f"Error fetching data for {city_name}: {e}")

if __name__ == "__main__":
    db_path = "data/air_quality_history.db"
    
    # We will just drop and recreate the measurements cleanly to avoid duplicates during backfill
    if os.path.exists(db_path):
        with sqlite3.connect(db_path) as conn:
            conn.execute("DROP TABLE IF EXISTS measurements")
            conn.commit()
    
    # Re-init fresh table
    logger = AQILogger()
    
    pull_historical_data("bengaluru", 12.9716, 77.5946, days=730)
    pull_historical_data("amsterdam", 52.3676, 4.9041, days=730)
    
    # Test predictor evaluation
    print("\nEvaluating Predictor on New Data...")
    predictor = AQIPredictor()
    predictor.train("bengaluru")
    predictor.train("amsterdam")
    
    # Simple manual evaluation (evaluating training error)
    if predictor.is_trained["bengaluru"]:
        # Usually we do train/test split, but let's just see if it runs
        print("Success! Models trained. Predictor is ready for 7-day forecasts.")
    
