import osmnx as ox
from pathlib import Path
import backend.config as config
from shapely.geometry import Point
import geopandas as gpd

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
        # G = ox.graph_from_place(config.CITY, network_type=config.NETWORK_TYPE)

        G = ox.graph_from_point(config.CENTER_POINT, dist=config.RADIUS, network_type=config.NETWORK_TYPE)

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
            print("No elevation data added")
            return G
        
        # Calculate edge grades
        G = ox.elevation.add_edge_grades(G, add_absolute=True)
        print("Elevation data added successfully")
        
        # Save updated network
        ox.save_graphml(G, config.NETWORK_FILE)
        
    except Exception as e:
        print(f"Error adding elevation: {e}")
    
    return G

def load_green_features(city):
    """Download green spaces from OSM"""
    tags = {
        'leisure': ['park', 'nature_reserve', 'garden'],
        'natural': ['water', 'wood', 'grassland'],
        'landuse': ['forest', 'grass', 'meadow']
    }
    gdf = ox.features_from_place(city, tags=tags)
    return gdf[gdf.geometry.notna()]

def add_greenery_scores(G, green_features, buffer_m=50):
    """Add greenery scores to edges based on proximity to parks"""
    
    green = green_features.to_crs(epsg=3857)
    green_union = green.geometry.union_all()
    
    rows = []
    for u, v, k in G.edges(keys=True):
        mid_lat = (G.nodes[u]['y'] + G.nodes[v]['y']) / 2
        mid_lng = (G.nodes[u]['x'] + G.nodes[v]['x']) / 2
        rows.append({'u': u, 'v': v, 'k': k, 'geometry': Point(mid_lng, mid_lat)})
    
    edges_gdf = gpd.GeoDataFrame(rows, crs=4326).to_crs(epsg=3857)
    inside = edges_gdf.geometry.within(green_union)
    dist = edges_gdf.geometry.distance(green_union)
    
    edges_gdf['greenery_score'] = 0.0
    edges_gdf.loc[inside, 'greenery_score'] = 1.0
    edges_gdf.loc[~inside, 'greenery_score'] = (1 - (dist[~inside] / buffer_m)).clip(0, 1)
    
    for _, row in edges_gdf.iterrows():
        G[row['u']][row['v']][row['k']]['greenery_score'] = row['greenery_score']
    
    print(f"Greenery scores added to {len(edges_gdf)} edges")
    return G