from flask import Flask, request, jsonify
from flask_cors import CORS
import osmnx as ox
import sys
from pathlib import Path

# Add backend to path so imports work
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend import config
from backend.services.network_manager import load_or_download_network, add_elevation_to_network, load_green_features, add_greenery_scores
from backend.services.route_stats import calculate_route_stats, route_nodes_to_coordinates
from backend.algorithms.simulated_annealing import simulated_annealing
from backend.algorithms.fitness import build_full_route

app = Flask(__name__)
CORS(app)

# Load network at startup
print("Initializing PATH API...")
G = load_or_download_network()

# Cache the place boundary polygon at startup
print("Loading region boundary...")
try:
    _place_gdf = ox.geocode_to_gdf(config.CITY)
    NETWORK_BOUNDARY_GEOJSON = _place_gdf.geometry.iloc[0].__geo_interface__
    print("Region boundary loaded.")
except Exception as e:
    print(f"Warning: Could not load place boundary, will use graph bounding box: {e}")
    NETWORK_BOUNDARY_GEOJSON = None

# Try to add elevation (will skip if no API key)
G = add_elevation_to_network(G, config.GOOGLE_MAPS_API_KEY)

try:
    print("Loading greenery data...")
    green_features = load_green_features(config.CITY)
    G = add_greenery_scores(G, green_features)
except Exception as e:
    print(f"Warning: Could not load greenery: {e}")
    print("Routes will work but without greenery optimization")

print(f"API ready! Network has {len(G.nodes())} nodes")

# Shared progress state updated during route generation
route_progress = {'current': 0, 'total': 0}

@app.route('/api/progress', methods=['GET'])
def get_progress():
    return jsonify(route_progress)

@app.route('/api/health', methods=['GET'])
def health_check():
    """Check if API is running"""
    return jsonify({
        'status': 'ok',
        'message': 'PATH API is running',
        'nodes': len(G.nodes()),
        'edges': len(G.edges())
    })

@app.route('/api/network-bounds', methods=['GET'])
def network_bounds():
    """Return the boundary polygon of the downloaded network region as GeoJSON."""
    if NETWORK_BOUNDARY_GEOJSON is not None:
        return jsonify({'geojson': NETWORK_BOUNDARY_GEOJSON})

    # Fallback: derive a bounding box from the graph nodes
    lats = [data['y'] for _, data in G.nodes(data=True)]
    lngs = [data['x'] for _, data in G.nodes(data=True)]
    bbox = [
        [min(lats), min(lngs)],
        [min(lats), max(lngs)],
        [max(lats), max(lngs)],
        [max(lats), min(lngs)],
    ]
    return jsonify({'bbox': bbox})

@app.route('/api/generate-route', methods=['POST'])
def generate_route():
    """
    Generate a route using simulated annealing.
    
    Expected JSON:
    {
        "start": {"lat": 42.5015, "lng": -71.2619},
        "distance": 5.0,
        "elevation": "flat" | "hilly" | "very-hilly"
    }
    """
    try:
        data = request.json
        
        # Validate input
        if not data or 'start' not in data or 'distance' not in data:
            return jsonify({'error': 'Missing required fields'}), 400
        
        start_lat = data['start']['lat']
        start_lng = data['start']['lng']
        target_distance = float(data['distance'])
        elevation_pref = data.get('elevation', 'flat')
        greenery_pref = data.get('greenery', 'medium')
        
        # Validate distance
        if target_distance < config.MIN_DISTANCE_KM or target_distance > config.MAX_DISTANCE_KM:
            return jsonify({'error': f'Distance must be between {config.MIN_DISTANCE_KM} and {config.MAX_DISTANCE_KM} km'}), 400
        
        # Find nearest node to start point
        start_node = ox.nearest_nodes(G, start_lng, start_lat)
        print(f"Start node: {start_node}")
        
        # Reset and wire up progress counter
        route_progress['current'] = 0
        route_progress['total'] = config.SA_MAX_ITERATIONS

        def update_progress(current, total):
            route_progress['current'] = current

        # Run simulated annealing
        waypoints = simulated_annealing(
            G,
            start_node,
            target_distance,
            elevation_pref,
            greenery_pref,
            max_iterations=config.SA_MAX_ITERATIONS,
            progress_callback=update_progress
        )
        
        # Build full route
        full_route = build_full_route(G, waypoints)
        
        if not full_route:
            return jsonify({'error': 'Could not generate valid route'}), 500
        
        # Convert to coordinates
        route_coords = route_nodes_to_coordinates(G, full_route)
        
        # Calculate stats
        stats = calculate_route_stats(G, full_route)
        
        return jsonify({
            'route': route_coords,
            'distance': stats['distance_km'],
            'elevation_gain': stats['elevation_gain_m'],
            'elevation_loss': stats['elevation_loss_m'],
            'num_waypoints': len(waypoints)
        })
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/nearest-node', methods=['POST'])
def nearest_node():
    """
    Find nearest valid road node to a clicked point.
    Returns the actual lat/lng of the nearest road.
    """
    try:
        data = request.json
        lat = data['lat']
        lng = data['lng']
        
        # Find nearest node in the network
        nearest = ox.nearest_nodes(G, lng, lat)
        
        # Get that node's actual coordinates
        node_lat = G.nodes[nearest]['y']
        node_lng = G.nodes[nearest]['x']
        
        return jsonify({
            'lat': node_lat,
            'lng': node_lng,
            'node_id': int(nearest)
        })
        
    except Exception as e:
        return jsonify({'error': 'No nearby roads found'}), 404

if __name__ == '__main__':
    print(f"Starting PATH API on port {config.PORT}...")
    app.run(debug=config.DEBUG, port=config.PORT, host='0.0.0.0')