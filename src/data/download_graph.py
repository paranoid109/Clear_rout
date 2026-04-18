import osmnx as ox
import os
import argparse

def download_city_graph(place_name="Bengaluru, India", base_path="data/bengaluru", network_types=["drive", "bike", "walk"]):
    """
    Downloads the street networks for a city for multiple modes and saves them locally.
    """
    os.makedirs(os.path.dirname(base_path), exist_ok=True)
    
    for net_type in network_types:
        save_path = f"{base_path}_{net_type}.graphml"
        print(f"Starting download for {place_name} ({net_type})...")
        
        try:
            G = ox.graph_from_place(place_name, network_type=net_type)
            print(f"Download complete for {net_type}. Nodes: {len(G.nodes)}, Edges: {len(G.edges)}")
            
            ox.save_graphml(G, save_path)
            print(f"Graph saved to {save_path}")
        except Exception as e:
            print(f"Failed to download {net_type} network: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download and cache OSM graphs for a city.")
    parser.add_argument("--place", type=str, default="Bengaluru, India", help="Place name for OSMnx")
    parser.add_argument("--base", type=str, default="data/bengaluru", help="Base path for graph files")
    parser.add_argument("--modes", type=str, nargs="+", default=["drive", "bike", "walk"], help="Network types")
    
    args = parser.parse_args()
    download_city_graph(place_name=args.place, base_path=args.base, network_types=args.modes)
