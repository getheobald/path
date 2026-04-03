import osmnx as ox

"""
Fitness Function for Route Optimization

The fitness function evaluates how "good" a route is based on:
1. Distance matching (weight: 200) - MUST be close to target
2. Elevation preference (weight: varies) - SHOULD match user preference
3. Loop quality (weight: 100) - Bonus for complete loops

Scoring:
- Perfect 5km route with correct elevation: ~1200 points
- 1km distance error: -200 points
- 100m unwanted elevation: -50 points

Tuning:
- Increase distance penalty if routes too far from target
- Adjust elevation weights if preferences not respected
"""

def calculate_fitness(G, route_waypoints, target_distance_km, elevation_pref='flat'):
    """
    Calculate fitness score for a route.
    Higher score = better route.
    
    Strategy:
    1. MUST match distance (hard constraint)
    2. SHOULD match elevation preference (soft constraint)
    3. Penalize backtracking/repeated edges
    """
    
    # build route through waypoints
    full_route = build_full_route(G, route_waypoints)
    
    if not full_route or len(full_route) < 2:
        return -100000  # Invalid route - very bad!
    
    # DISTANCE SCORE (most important)
    total_distance = 0
    for i in range(len(full_route) - 1):
        u, v = full_route[i], full_route[i+1]
        if G.has_edge(u, v):
            total_distance += G.edges[u, v, 0].get('length', 0)
    
    actual_distance_km = total_distance / 1000
    distance_error = abs(actual_distance_km - target_distance_km)
    
    # heavy penalty for distance errors
    # i.e. if we want 5km and get 3km, that's 2km error = -400 points
    distance_score = 1000 - (distance_error * 200)
    
    # 2. ELEVATION SCORE
    elevation_score = 0
    if 'elevation' in G.nodes[full_route[0]]:
        elevation_gain = calculate_elevation_gain(G, full_route)
        
        if elevation_pref == 'flat':
            # penalize ANY elevation gain
            # 100m gain = -50 points
            elevation_score = -(elevation_gain * 0.5)
            
        elif elevation_pref == 'hilly':
            # reward if between 100-400m gain
            # perfect is 250m
            ideal_gain = 250
            if elevation_gain < 50:
                # too flat
                elevation_score = -100
            elif 100 <= elevation_gain <= 400:
                # good! closer to 250 is better
                elevation_score = 200 - abs(elevation_gain - ideal_gain) * 0.5
            else:
                # Too hilly
                elevation_score = -(elevation_gain - 400) * 0.3
                
        elif elevation_pref == 'very-hilly':
            # reward high elevation
            # more is better, to a point
            if elevation_gain < 200:
                elevation_score = -100
            else:
                elevation_score = min(elevation_gain * 0.4, 300)  # cap at 300 points
    
    # 3. LOOP QUALITY (bonus)
    loop_score = 0
    # check if route ends near start
    start_node = full_route[0]
    end_node = full_route[-1]
    
    if start_node == end_node:
        # perfect loop
        loop_score = 100
    elif G.has_edge(end_node, start_node):
        # ends one edge away from start
        loop_score = 50
    
    # TOTAL SCORE
    total_score = distance_score + elevation_score + loop_score
    
    return total_score

def build_full_route(G, waypoints):
    """
    Build full route through waypoints using shortest paths.
    
    Returns:
        List of node IDs forming complete route
    """
    full_route = []
    
    for i in range(len(waypoints) - 1):
        try:
            # Find shortest path between consecutive waypoints
            segment = ox.shortest_path(G, waypoints[i], waypoints[i+1], weight='length')
            
            if segment is None:
                return None  # No path exists
            
            # Add segment (avoid duplicating nodes at junctions)
            if full_route:
                full_route.extend(segment[1:])
            else:
                full_route.extend(segment)
        except Exception as e:
            print(f"Error finding path: {e}")
            return None
    
    return full_route

def calculate_elevation_gain(G, route_nodes):
    """Calculate total elevation gain along route"""
    elevation_gain = 0
    
    for i in range(len(route_nodes) - 1):
        node_current = route_nodes[i]
        node_next = route_nodes[i+1]
        
        if 'elevation' in G.nodes[node_current] and 'elevation' in G.nodes[node_next]:
            elev_change = G.nodes[node_next]['elevation'] - G.nodes[node_current]['elevation']
            if elev_change > 0:
                elevation_gain += elev_change
    
    return elevation_gain