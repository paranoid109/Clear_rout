import osmnx as ox
import networkx as nx
import os
import numpy as np
import sys

# Add src to path if running directly
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from src.prediction.ventilation import MinuteVentilationModel
from src.prediction.spatial_interpolator import SpatialInterpolator

class AirRouter:
    # Mode-specific AQI sensitivity multipliers
    MODE_SENSITIVITY = {
        "car": 1.0,
        "bike": 1.5,
        "walk": 2.0
    }

    def __init__(self, base_graph_path="data/amsterdam"):
        self.base_graph_path = base_graph_path
        self.graphs = {} # Cache for loaded graphs by mode
        self.current_mode = "drive"
        self.G = None
        self.ventilation_model = MinuteVentilationModel()
        self.spatial_interpolator = SpatialInterpolator()
        self.set_mode("drive")

    def set_mode(self, mode: str):
        """
        Switches the routing graph to the specified mode.
        mode: 'drive', 'bike', or 'walk'
        """
        # Map input friendly names to graph suffixes
        net_type_map = {"car": "drive", "bike": "bike", "walk": "walk"}
        net_type = net_type_map.get(mode, mode)
        
        if net_type not in self.graphs:
            self._load_graph(net_type)
        
        self.G = self.graphs[net_type]
        self.current_mode = mode
        print(f"Router mode set to: {mode}")

    def _load_graph(self, net_type: str):
        graph_file = f"{self.base_graph_path}_{net_type}.graphml"
        if not os.path.exists(graph_file):
            # Try fallback to original name if only one exists
            if os.path.exists(f"{self.base_graph_path}.graphml"):
                graph_file = f"{self.base_graph_path}.graphml"
            else:
                raise FileNotFoundError(f"Graph file for {net_type} not found.")
        
        print(f"Loading {net_type} graph from {graph_file}...")
        try:
            G = ox.load_graphml(graph_file)
        except MemoryError:
            print("MemoryError loading graphml! Creating a mock graph to prevent crash.")
            G = nx.MultiDiGraph()
            # We don't populate nodes, we just let it be empty and catch it in get_route

        # Check if speeds / times exist before adding to avoid osmnx errors on mock
        if len(G.edges) > 0 and 'travel_time' not in next(iter(G.edges(data=True)))[2]:
            try:
                G = ox.add_edge_speeds(G)
                G = ox.add_edge_travel_times(G)
            except Exception:
                pass
        
        # Initialize AQI
        for u, v, k, data in G.edges(data=True, keys=True):
            data['aqi'] = 50.0
            
        self.graphs[net_type] = G

    def update_aqi_on_graph(self, aqi_data: list = None):
        """
        Projects AQI onto graph using spatial interpolator and calculates mode-specific penalties.
        Uses vectorized batch prediction for performance.
        """
        if aqi_data is None:
            aqi_data = []
        import numpy as np
        
        # Pedestrians and Cyclists have higher respiratory sensitivity
        sensitivity = self.MODE_SENSITIVITY.get(self.current_mode, 1.0)
        
        # Train interpolator dynamically on current API snapshot
        self.spatial_interpolator.train(aqi_data)
        
        # Collect all edge data for batch processing
        edges = list(self.G.edges(data=True, keys=True))
        if not edges:
            return
        
        if self.spatial_interpolator.is_trained:
            # Build coordinate and highway type arrays for batch prediction
            coords = []
            highway_types = []
            for u, v, k, data in edges:
                node_u = self.G.nodes[u]
                coords.append([node_u['y'], node_u['x']])
                ht = data.get('highway', 'residential')
                if isinstance(ht, list):
                    ht = ht[0]
                highway_types.append(ht)
            
            coords_arr = np.array(coords)
            aqi_values = self.spatial_interpolator.interpolate_batch(coords_arr, highway_types)
            
            # Apply results back to edges
            for i, (u, v, k, data) in enumerate(edges):
                data['aqi'] = float(aqi_values[i])
                travel_time = data.get('travel_time', 1.0)
                data['aqi_penalty'] = travel_time * (1 + (data['aqi'] * sensitivity / 100.0))
        else:
            # No interpolator — use safe defaults
            for u, v, k, data in edges:
                data['aqi'] = 50.0
                travel_time = data.get('travel_time', 1.0)
                data['aqi_penalty'] = travel_time * (1 + (50.0 * sensitivity / 100.0))

    def get_route(self, start_coords, end_coords, weight="travel_time"):
        """
        Finds the shortest route. Falls back to a straight line if graph is empty or disconnected.
        """
        if len(self.G.nodes) == 0:
            raise ValueError("Graph is empty (possibly due to MemoryError)")
            
        orig_node, dist_orig = ox.distance.nearest_nodes(self.G, X=start_coords[1], Y=start_coords[0], return_dist=True)
        dest_node, dist_dest = ox.distance.nearest_nodes(self.G, X=end_coords[1], Y=end_coords[0], return_dist=True)
        
        # If distance is > 10km (approx 0.1 degrees), it's grossly out of bounds
        if dist_orig > 10000 or dist_dest > 10000:
            raise ValueError("Point is too far from city center/graph coverage.")

        route = nx.shortest_path(self.G, orig_node, dest_node, weight=weight)
        if len(route) < 2:
            raise ValueError("Route too short")

        route_gdf = ox.routing.route_to_gdf(self.G, route)
        
        total_length = route_gdf['length'].sum() if 'length' in route_gdf.columns else 0
        total_time = route_gdf['travel_time'].sum() if 'travel_time' in route_gdf.columns else 0
        avg_aqi = route_gdf['aqi'].mean() if 'aqi' in route_gdf.columns else 50
        
        # Calculate physiological impact using minute ventilation
        # We assume 0% incline since we don't have elevation on edges yet (Placeholder for Future Elev Integration)
        avg_speed_kmh = (total_length / 1000.0) / (total_time / 3600.0) if total_time > 0 else 0
        ve = self.ventilation_model.predict_ve(self.current_mode, avg_speed_kmh, 0.0)
        pm25_ug = self.ventilation_model.calculate_pm25_inhaled(avg_aqi, ve, total_time / 60.0)
        
        return {
            "route": route,
            "distance_km": total_length / 1000.0,
            "time_min": total_time / 60.0,
            "aqi_mean": avg_aqi,
            "exposure_index": avg_aqi * (total_time / 60.0),
            "pm25_inhaled_ug": pm25_ug,
            "nodes": route,
            "path": [[self.G.nodes[n]['y'], self.G.nodes[n]['x']] for n in route],
            "is_fallback": False
        }

    def get_dual_routes(self, start_coords, end_coords, mode="car", aqi_data: list = None):
        """
        Calculates both the fastest and the cleanest route for the given mode.
        """
        if aqi_data is None:
            aqi_data = []
        self.set_mode(mode)
        self.update_aqi_on_graph(aqi_data)
        
        fastest = self.get_route(start_coords, end_coords, weight="travel_time")
        cleanest = self.get_route(start_coords, end_coords, weight="aqi_penalty")
        
        return fastest, cleanest

if __name__ == "__main__":
    # Example usage:
    # Router needs the file to exist, so this is just a structure for now.
    pass
