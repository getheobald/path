import osmnx as ox
import config

print("Downloading downtown Boston network")
print("This will take 2-5 minutes and download ~50,000 nodes")

center_point = (42.3601, -71.0589)  # Downtown Bos
distance = 3000  # 3km radius

# G = ox.graph_from_place(config.CITY, network_type=config.NETWORK_TYPE) this was super slow - trying with just downtown for testing
G = ox.graph_from_point(center_point, dist=distance, network_type='bike')
print(f"Downloaded {len(G.nodes())} nodes, {len(G.edges())} edges")

# Try to add elevation (may fail without API key)
print("Attempting to add elevation data")
try:
    if config.GOOGLE_MAPS_API_KEY:
        G = ox.elevation.add_node_elevations_google(G, api_key=config.GOOGLE_MAPS_API_KEY)
        G = ox.elevation.add_edge_grades(G)
        print("Elevation data added")
    else:
        print("No API key - skipping elevation (routes will work but no elevation matching)")
except Exception as e:
    print(f"Could not add elevation: {e}")

# save
print(f"Saving to {config.NETWORK_FILE}...")
ox.save_graphml(G, config.NETWORK_FILE)
print("Network saved!")