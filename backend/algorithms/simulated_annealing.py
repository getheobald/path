import random
import math
import osmnx as ox
from backend.algorithms.fitness import calculate_fitness

def simulated_annealing(G, start_node, target_distance_km, elevation_pref='flat', max_iterations=500):
    """
    Generate a route using simulated annealing.
    
    Args:
        G: OSMnx graph with elevation data
        start_node: Starting node ID
        target_distance_km: Desired route distance in km
        elevation_pref: 'flat', 'hilly', or 'very-hilly'
        max_iterations: Number of iterations to run
        
    Returns:
        List of node IDs forming the route
    """
    print(f"Starting simulated annealing: target={target_distance_km}km, pref={elevation_pref}")
    
    # Initialize with random route
    current_route = generate_random_route(G, start_node, num_waypoints=5)
    current_score = calculate_fitness(G, current_route, target_distance_km, elevation_pref)
    
    best_route = current_route.copy()
    best_score = current_score
    
    temperature = 100.0
    cooling_rate = 0.95
    
    for iteration in range(max_iterations):
        # Generate neighbor by mutating current route
        new_route = mutate_route(G, current_route)
        new_score = calculate_fitness(G, new_route, target_distance_km, elevation_pref)
        
        # Decide whether to accept
        if accept_move(current_score, new_score, temperature):
            current_route = new_route
            current_score = new_score
            
            if new_score > best_score:
                best_route = new_route.copy()
                best_score = new_score
        
        # Cool down
        temperature *= cooling_rate
        
        # Log progress
        if iteration % 100 == 0:
            print(f"Iteration {iteration}: Best score = {best_score:.2f}, Temp = {temperature:.2f}")
    
    print(f"Finished! Best score: {best_score:.2f}")
    return best_route

def generate_random_route(G, start_node, num_waypoints):
    """Generate initial random route with waypoints near start"""
    import osmnx as ox
    
    # Get nodes within reasonable distance of start (e.g., 2km radius)
    # This ensures route explores area near starting point
    start_point = (G.nodes[start_node]['y'], G.nodes[start_node]['x'])
    
    # Get all nodes within 2km
    nearby_nodes = []
    for node in G.nodes():
        node_point = (G.nodes[node]['y'], G.nodes[node]['x'])
        # Simple distance check (not perfect but fast)
        lat_diff = abs(node_point[0] - start_point[0])
        lng_diff = abs(node_point[1] - start_point[1])
        if lat_diff < 0.01 and lng_diff < 0.01:  # Roughly 1km
            nearby_nodes.append(node)
    
    # If we found enough nearby nodes, sample from them
    if len(nearby_nodes) >= num_waypoints:
        waypoints = random.sample(nearby_nodes, k=num_waypoints)
    else:
        # Fall back to all nodes if area too small
        all_nodes = list(G.nodes())
        waypoints = random.sample(all_nodes, k=min(num_waypoints, len(all_nodes)))
    
    # Create loop: start -> waypoints -> start
    route = [start_node] + waypoints + [start_node]
    
    return route

def mutate_route(G, route):
    """Make a small random change to the route"""
    new_route = route.copy()
    all_nodes = list(G.nodes())
    
    mutation_type = random.choice(['change_waypoint', 'swap_waypoints', 'move_waypoint'])
    
    if mutation_type == 'change_waypoint' and len(route) > 2:
        # Change one waypoint (not start/end)
        idx = random.randint(1, len(route) - 2)
        new_route[idx] = random.choice(all_nodes)
    
    elif mutation_type == 'swap_waypoints' and len(route) > 3:
        # Swap two waypoints
        idx1 = random.randint(1, len(route) - 2)
        idx2 = random.randint(1, len(route) - 2)
        new_route[idx1], new_route[idx2] = new_route[idx2], new_route[idx1]
    
    elif mutation_type == 'move_waypoint' and len(route) > 2:
        # Move a waypoint to a nearby node
        idx = random.randint(1, len(route) - 2)
        current_node = route[idx]
        
        # Get neighbors of current node
        neighbors = list(G.neighbors(current_node))
        if neighbors:
            new_route[idx] = random.choice(neighbors)
    
    return new_route

def accept_move(current_score, new_score, temperature):
    """Metropolis criterion for accepting moves"""
    if new_score > current_score:
        return True
    else:
        # Accept worse solutions probabilistically
        delta = new_score - current_score
        probability = math.exp(delta / temperature) if temperature > 0 else 0
        return random.random() < probability