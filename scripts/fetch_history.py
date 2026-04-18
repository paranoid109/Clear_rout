import requests
import sqlite3
import pandas as pd
from datetime import datetime
import os
import sys

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from src.data.logger import AQILogger

def fetch_and_store_history(db_path="data/air_quality_history.db", lat=12.9716, lon=77.5946, city="bengaluru", days=90):
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    # 1. Fetch data from Open-Meteo
    url = f"https://air-quality-api.open-meteo.com/v1/air-quality?latitude={lat}&longitude={lon}&hourly=us_aqi&past_days={days}"
    print(f"Fetching historic data from Open-Meteo for {city} (past {days} days)...")
    response = requests.get(url)
    
    if response.status_code != 200:
        print("Failed to fetch data")
        return
        
    data = response.json()
    hourly = data.get("hourly", {})
    times = hourly.get("time", [])
    aqis = hourly.get("us_aqi", [])
    
    # 2. Filter out Nones
    valid_records = []
    for t, aqi in zip(times, aqis):
        if aqi is not None:
             dt = datetime.fromisoformat(t)
             valid_records.append({
                 "timestamp": dt.strftime("%Y-%m-%d %H:%M:%S"),
                 "city": city,
                 "fused_aqi": aqi,
                 "api_aqi": aqi,
                 "sensor_aqi": aqi
             })
             
    if not valid_records:
        print("No valid historic data retrieved.")
        return
        
    # 3. Store into DB using the same schema as logger.py
    with sqlite3.connect(db_path) as conn:
        # Ensure table exists with correct schema
        conn.execute('''
            CREATE TABLE IF NOT EXISTS measurements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                city TEXT DEFAULT 'bengaluru',
                fused_aqi REAL,
                api_aqi REAL,
                sensor_aqi REAL
            )
        ''')
        
        # Clear existing data for this city to avoid duplicates
        conn.execute("DELETE FROM measurements WHERE city = ?", (city,))
        
        df = pd.DataFrame(valid_records)
        df.to_sql('measurements', conn, if_exists='append', index=False)
        print(f"Successfully inserted {len(df)} historical records for {city} into SQLite.")

if __name__ == "__main__":
    fetch_and_store_history(city="bengaluru", lat=12.9716, lon=77.5946)
    fetch_and_store_history(city="amsterdam", lat=52.3676, lon=4.9041)
