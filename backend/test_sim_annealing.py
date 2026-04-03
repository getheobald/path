import osmnx as ox
from algorithms.simulated_annealing import simulated_annealing
from algorithms.fitness import build_full_route
from services.route_stats import calculate_route_stats

# load network
print("Loading network...")
G = ox.load_graphml('boston_network.graphml')

# pick a test start point in downtown Bos
start_node = ox.nearest_nodes(G, -71.0589, 42.3601)

print(f"\nStart node: {start_node}")

# Test 1: 5km flat route
print("\nTest 1: 5km flat route")
waypoints = simulated_annealing(G, start_node, 5.0, 'flat', max_iterations=200)
full_route = build_full_route(G, waypoints)
stats = calculate_route_stats(G, full_route)
print(f"Distance: {stats['distance_km']:.2f} km (target: 5.0)")
print(f"Elevation: {stats['elevation_gain_m']:.0f}m")
print(f"Result: {'good!' if abs(stats['distance_km'] - 5.0) < 0.75 else 'failed :('}")

# Test 2: 10km hilly route
print("\nTest 2: 10km hilly route")
waypoints = simulated_annealing(G, start_node, 10.0, 'hilly', max_iterations=200)
full_route = build_full_route(G, waypoints)
stats = calculate_route_stats(G, full_route)
print(f"Distance: {stats['distance_km']:.2f} km (target: 10.0)")
print(f"Elevation: {stats['elevation_gain_m']:.0f}m")
print(f"Result: {'good!' if abs(stats['distance_km'] - 10.0) < 1.5 else 'failed :('}")