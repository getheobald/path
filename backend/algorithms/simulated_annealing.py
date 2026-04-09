import random
import math
import osmnx as ox
from algorithms.fitness import calculate_fitness

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
    
    # initialize with random route
    current_route = generate_random_route(G, start_node, num_waypoints=5)
    current_score = calculate_fitness(G, current_route, target_distance_km, elevation_pref)
    
    best_route = current_route.copy()
    best_score = current_score
    
    temp = 100.0
    decay = 0.98
    
    for iteration in range(max_iterations):
        # generate neighbor by mutating current route
        new_route = mutate_route(G, current_route)
        new_score = calculate_fitness(G, new_route, target_distance_km, elevation_pref)
        
        # decide whether to accept
        if accept_move(current_score, new_score, temp):
            current_route = new_route
            current_score = new_score
            
            if new_score > best_score:
                best_route = new_route.copy()
                best_score = new_score
        
        # cool down
        temp *= decay
        
        # log progress
        if iteration % 100 == 0:
            print(f"Iteration {iteration}: Best score = {best_score:.2f}, Temp = {temp:.2f}")
    
    print(f"Finished! Best score: {best_score:.2f}")
    return best_route

def generate_random_route(G, start_node, num_waypoints):
    """
    Generate initial random route with waypoints near start
    Better initial guess causes faster convergence
    """
    import osmnx as ox
    
    # pick waypoints in expanding circles around start
    start_point = (G.nodes[start_node]['y'], G.nodes[start_node]['x'])
    
    all_nodes = list(G.nodes())
    
    # calculate rough distances to all nodes (fast approximation)
    nearby_nodes = []
    for node in all_nodes:
        node_point = (G.nodes[node]['y'], G.nodes[node]['x'])
        # simple distance check (1 degree lat or lng is around 111km)
        lat_diff = abs(node_point[0] - start_point[0])
        lng_diff = abs(node_point[1] - start_point[1])
        
        # keep nodes within 3km ish radius
        if lat_diff < 0.03 and lng_diff < 0.03:
            nearby_nodes.append(node)
    
    # if we found enough nearby nodes, use them
    if len(nearby_nodes) >= num_waypoints:
        waypoints = random.sample(nearby_nodes, k=num_waypoints)
    else:
        # fall back to any nodes
        waypoints = random.sample(all_nodes, k=min(num_waypoints, len(all_nodes)))
    
    # create loop from start -> waypoints -> start
    route = [start_node] + waypoints + [start_node]
    
    return route

def mutate_route(G, route):
    """Make a small random change to the route"""
    new_route = route.copy()
    all_nodes = list(G.nodes())
    
    mutation_type = random.choice(['change_waypoint', 'swap_waypoints', 'move_waypoint'])
    
    if mutation_type == 'change_waypoint' and len(route) > 2:
        # change one waypoint (not start or end)
        idx = random.randint(1, len(route) - 2)
        new_route[idx] = random.choice(all_nodes)
    
    elif mutation_type == 'swap_waypoints' and len(route) > 3:
        # swap two waypoints
        idx1 = random.randint(1, len(route) - 2)
        idx2 = random.randint(1, len(route) - 2)
        new_route[idx1], new_route[idx2] = new_route[idx2], new_route[idx1]
    
    elif mutation_type == 'move_waypoint' and len(route) > 2:
        # move a waypoint to a nearby node
        idx = random.randint(1, len(route) - 2)
        current_node = route[idx]
        
        # get neighbors of current node
        neighbors = list(G.neighbors(current_node))
        if neighbors:
            new_route[idx] = random.choice(neighbors)
    
    return new_route

def accept_move(current_score, new_score, temp):
    """Determine if random move is acceptable or not"""
    if new_score > current_score:
        return True
    else:
        # accept worse solutions based on temp decay
        delta = new_score - current_score
        probability = math.exp(delta / temp) if temp > 0 else 0
        return random.random() < probability