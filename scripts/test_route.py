import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.routing.basic_router import AirRouter
import osmnx as ox

def test_routing():
    # Dam Square coordinates
    start_coords = (52.3731, 4.8926)
    # Rijksmuseum coordinates
    end_coords = (52.3600, 4.8852)
    
    graph_path = "data/amsterdam"
    
    if not os.path.exists(f"{graph_path}_drive.graphml"):
        print("Graph file not found. attempting to download...")
        from src.data.download_graph import download_amsterdam_graph
        download_amsterdam_graph(graph_path)
    
    try:
        router = AirRouter(graph_path)
        print(f"\nCalculating route from {start_coords} to {end_coords}...")
        
        result = router.get_route(start_coords, end_coords)
        
        print(f"Success!")
        print(f"Distance: {result['distance_km']:.2f} km")
        print(f"Estimated Time: {result['time_min']:.2f} min")
        print(f"Number of nodes in route: {len(result['nodes'])}")
        
    except Exception as e:
        print(f"Error during routing test: {e}")

if __name__ == "__main__":
    test_routing()
