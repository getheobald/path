import osmnx as ox
from pathlib import Path
import backend.config as config

def load_or_download_network():
    """
    Load network from cache or download if not exists.
    
    Returns:
        OSMnx graph
    """
    network_file = config.NETWORK_FILE
    
    if network_file.exists():
        print(f"Loading network from {network_file}...")
        G = ox.load_graphml(network_file)
        print(f"Loaded {len(G.nodes())} nodes, {len(G.edges())} edges")
    else:
        print(f"Downloading network for {config.CITY}...")
        G = ox.graph_from_place(config.CITY, network_type=config.NETWORK_TYPE)
        print(f"Downloaded {len(G.nodes())} nodes, {len(G.edges())} edges")
        
        # Save for next time
        print(f"Saving to {network_file}...")
        ox.save_graphml(G, network_file)
    
    return G

def add_elevation_to_network(G, api_key=None):
    """
    Add elevation data to network.
    
    Args:
        G: OSMnx graph
        api_key: Google Maps API key (optional)
        
    Returns:
        Graph with elevation data
    """
    # Check if already has elevation
    sample_node = list(G.nodes())[0]
    if 'elevation' in G.nodes[sample_node]:
        print("Network already has elevation data")
        return G
    
    print("Adding elevation data...")
    
    try:
        if api_key:
            # Use Google API
            G = ox.elevation.add_node_elevations_google(G, api_key=api_key)
        else:
            # Use free raster file (if available)
            # TODO: Add raster file path
            print("Warning: No elevation data added (need API key or raster file)")
            return G
        
        # Calculate edge grades
        G = ox.elevation.add_edge_grades(G, add_absolute=True)
        print("Elevation data added successfully")
        
        # Save updated network
        ox.save_graphml(G, config.NETWORK_FILE)
        
    except Exception as e:
        print(f"Error adding elevation: {e}")
    
    return G