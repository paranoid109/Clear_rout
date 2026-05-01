import requests
import time
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional

class AQIAPIClient:
    def __init__(self):
        self.last_fetched = None
        self.cache = None

    def get_measurements(self) -> List[Dict]:
        raise NotImplementedError

class LuchtmeetnetClient(AQIAPIClient):
    """Client for the Dutch Luchtmeetnet API."""
    BASE_URL = "https://api.luchtmeetnet.nl/open_api"

    def __init__(self):
        super().__init__()
        self.station_coords = self._load_station_coords()

    def _load_station_coords(self):
        try:
            with open('data/luchtmeetnet_stations.json', 'r') as f:
                import json
                return json.load(f)
        except Exception:
            return {}

    def get_measurements(self) -> List[Dict]:
        # Simple implementation fetching latest measurements for Amsterdam area
        # Note: In a production system, we'd filter by bbox or coordinates.
        try:
            response = requests.get(f"{self.BASE_URL}/measurements", timeout=10)
            if response.status_code == 200:
                data = response.json().get('data', [])
                # Normalize data format
                normalized = []
                for item in data:
                    station_num = item.get('station_number')
                    coords = self.station_coords.get(station_num, {})
                    normalized.append({
                        "station": station_num,
                        "value": item.get('value'),
                        "formula": item.get('formula'),
                        "timestamp": item.get('timestamp_measured'),
                        "lat": coords.get('lat'),
                        "lon": coords.get('lon')
                    })
                return normalized
            return []
        except Exception as e:
            print(f"Error fetching from Luchtmeetnet: {e}")
            return []

class OpenAQv3Client(AQIAPIClient):
    """Client for the OpenAQ v3 API."""
    BASE_URL = "https://api.openaq.org/v3"

    def __init__(self, api_key: str):
        super().__init__()
        self.headers = {"X-API-Key": api_key}

    def get_measurements(self, city="Amsterdam") -> List[Dict]:
        try:
            # 1. Get locations for city
            params = {"city": city, "limit": 10}
            resp = requests.get(f"{self.BASE_URL}/locations", params=params, headers=self.headers, timeout=10)
            if resp.status_code != 200: return []
            
            locations = resp.json().get('results', [])
            normalized = []
            
            for loc in locations:
                loc_id = loc.get('id')
                # 2. Get latest for each location
                latest_resp = requests.get(f"{self.BASE_URL}/locations/{loc_id}/latest", headers=self.headers, timeout=10)
                if latest_resp.status_code == 200:
                    results = latest_resp.json().get('results', [])
                    for res in results:
                        normalized.append({
                            "station": loc.get('name'),
                            "value": res.get('value'),
                            "formula": res.get('parameter', {}).get('name'),
                            "timestamp": res.get('datetime', {}).get('utc'),
                            "lat": loc.get('coordinates', {}).get('latitude'),
                            "lon": loc.get('coordinates', {}).get('longitude')
                        })
            return normalized
        except Exception as e:
            print(f"Error fetching from OpenAQ v3: {e}")
            return []

class WAQIClient(AQIAPIClient):
    """Client for the World Air Quality Index (WAQI) API."""
    BASE_URL = "https://api.waqi.info/feed"

    def __init__(self, token: str):
        super().__init__()
        self.token = token

    def get_measurements(self, city="amsterdam") -> List[Dict]:
        try:
            url = f"{self.BASE_URL}/{city}/?token={self.token}"
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                data = resp.json().get('data', {})
                if not data: return []
                
                # WAQI returns a single station result for city search
                return [{
                    "station": data.get('city', {}).get('name'),
                    "value": data.get('aqi'),
                    "formula": data.get('dominentpol'),
                    "timestamp": data.get('time', {}).get('iso'),
                    "lat": data.get('city', {}).get('geo', [0, 0])[0],
                    "lon": data.get('city', {}).get('geo', [0, 0])[1]
                }]
            return []
        except Exception as e:
            print(f"Error fetching from WAQI: {e}")
            return []

class IQAirClient(AQIAPIClient):
    """Client for the IQAir (AirVisual) API."""
    BASE_URL = "https://api.airvisual.com/v2"

    def __init__(self, api_key: str):
        super().__init__()
        self.api_key = api_key

    def get_measurements(self, city="Amsterdam", state="North Holland", country="Netherlands") -> List[Dict]:
        try:
            params = {"city": city, "state": state, "country": country, "key": self.api_key}
            resp = requests.get(f"{self.BASE_URL}/city", params=params, timeout=10)
            if resp.status_code == 200:
                data = resp.json().get('data', {})
                pollution = data.get('current', {}).get('pollution', {})
                return [{
                    "station": f"{city}, {country}",
                    "value": pollution.get('aqius'),
                    "formula": pollution.get('mainus'),
                    "timestamp": pollution.get('ts'),
                    "lat": data.get('location', {}).get('coordinates', [0, 0])[1],
                    "lon": data.get('location', {}).get('coordinates', [0, 0])[0]
                }]
            return []
        except Exception as e:
            print(f"Error fetching from IQAir: {e}")
            return []

class AQIManager:
    CACHE_FILE = "data/aqi_cache.json"

    def __init__(self):
        self.clients = {
            "luchtmeetnet": LuchtmeetnetClient(),
            "openaq": OpenAQv3Client("245040942ba39785b1ab111fa1a6c1c0a7047cc5cf9e06d1dccc7336f778637b"),
            "waqi": WAQIClient("c02b455c0d2578d140e17964973cf577232fed88"),
            "iqair": IQAirClient("1d27ad69-c3fa-4f27-a5a4-3f614dba9403")
        }
        self.health_status = {name: True for name in self.clients}
        self.last_fused_cache = 50.0 
        self._load_cache()

    def _load_cache(self):
        if os.path.exists(self.CACHE_FILE):
            try:
                with open(self.CACHE_FILE, 'r') as f:
                    import json
                    data = json.load(f)
                    self.last_fused_cache = data.get('aqi', 50.0)
            except:
                pass

    def _save_cache(self, aqi):
        os.makedirs(os.path.dirname(self.CACHE_FILE), exist_ok=True)
        try:
            with open(self.CACHE_FILE, 'w') as f:
                import json
                json.dump({'aqi': aqi, 'timestamp': datetime.now().isoformat()}, f)
        except:
            pass

    def fetch_all_safe(self) -> Dict:
        """
        Fetches data and returns status flags as per SOP Section 8.
        Returns: { 'data': [...], 'status': 'API_FULL' | 'DEGRADED' | 'SENSOR_ONLY' | 'CACHE_ONLY' }
        """
        all_data = []
        down_count = 0
        total_apis = len(self.clients)

        for name, client in self.clients.items():
            data = client.get_measurements()
            if data:
                all_data.extend(data)
                self.health_status[name] = True
            else:
                self.health_status[name] = False
                down_count += 1
        
        
        status = "API_FULL"
        if down_count > 0 and down_count < total_apis:
            status = "DEGRADED"
        elif down_count >= total_apis:
            status = "CACHE_ONLY"

        return {
            "data": all_data,
            "status": status,
            "count_down": down_count
        }

    def get_average_aqi(self) -> Dict:
        """Returns avg AQI and status flag."""
        result = self.fetch_all_safe()
        data = result['data']
        
        if not data:
            return {"value": self.last_fused_cache, "status": "CACHE_ONLY"}
        
        values = [d['value'] for d in data if d['value'] is not None]
        avg = sum(values) / len(values) if values else self.last_fused_cache
        
        self._save_cache(avg)
        return {"value": avg, "status": result['status']}

if __name__ == "__main__":
    manager = AQIManager()
    print("Fetching live AQI data...")
    result = manager.get_average_aqi()
    print(f"Aggregated average AQI value: {result['value']:.2f} (Status: {result['status']})")
