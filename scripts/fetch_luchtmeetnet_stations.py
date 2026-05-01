import requests
import json
import os
import concurrent.futures

BASE_URL = "https://api.luchtmeetnet.nl/open_api"

def fetch_station(number):
    try:
        resp = requests.get(f"{BASE_URL}/stations/{number}", timeout=10)
        if resp.status_code == 200:
            data = resp.json().get('data', {})
            geom = data.get('geometry', {})
            if geom and geom.get('type') == 'point':
                coords = geom.get('coordinates', [])
                if len(coords) == 2:
                    return number, {'lon': coords[0], 'lat': coords[1]}
    except Exception:
        pass
    return number, None

def main():
    print("Fetching station list...")
    page = 1
    stations = []
    while True:
        resp = requests.get(f"{BASE_URL}/stations?page={page}", timeout=10)
        if resp.status_code == 200:
            data = resp.json().get('data', [])
            if not data: break
            stations.extend([s['number'] for s in data])
            pag = resp.json().get('pagination', {})
            if page >= pag.get('last_page', 1): break
            page += 1
        else:
            break
            
    print(f"Found {len(stations)} stations. Fetching coordinates...")
    station_coords = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        results = executor.map(fetch_station, stations)
        for num, coords in results:
            if coords:
                station_coords[num] = coords
                
    os.makedirs('data', exist_ok=True)
    with open('data/luchtmeetnet_stations.json', 'w') as f:
        json.dump(station_coords, f)
    print(f"Saved {len(station_coords)} station coordinates.")

if __name__ == "__main__":
    main()
