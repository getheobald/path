import osmnx as ox

def calculate_fitness(G, route_waypoints, target_distance_km, elevation_pref='flat'):
    """
    Calculate fitness score for a route.
    Higher score = better route.
    
    Args:
        G: OSMnx graph
        route_waypoints: List of node IDs (waypoints)
        target_distance_km: Target distance in km
        elevation_pref: 'flat', 'hilly', or 'very-hilly'
        
    Returns:
        Fitness score (float)
    """
    # Build full route through waypoints
    full_route = build_full_route(G, route_waypoints)
    
    if not full_route or len(full_route) < 2:
        return -10000  # Invalid route
    
    # Calculate distance
    total_distance = 0
    for i in range(len(full_route) - 1):
        u, v = full_route[i], full_route[i+1]
        if G.has_edge(u, v):
            total_distance += G.edges[u, v, 0].get('length', 0)
    
    actual_distance_km = total_distance / 1000
    
    # Distance penalty: heavily penalize if too far from target
    distance_error = abs(actual_distance_km - target_distance_km)
    distance_score = 1000 - (distance_error * 200)  # Each km off = -200 points
    
    # Elevation score (if elevation data exists)
    elevation_score = 0
    if 'elevation' in G.nodes[full_route[0]]:
        elevation_gain = calculate_elevation_gain(G, full_route)
        
        if elevation_pref == 'flat':
            # Penalize elevation gain
            elevation_score = -elevation_gain * 0.5
        elif elevation_pref == 'hilly':
            # Reward moderate elevation (100-300m)
            if 100 <= elevation_gain <= 300:
                elevation_score = 100
            else:
                elevation_score = -(abs(elevation_gain - 200) * 0.3)
        elif elevation_pref == 'very-hilly':
            # Reward high elevation
            elevation_score = elevation_gain * 0.3
    
    # Total score
    total_score = distance_score + elevation_score
    
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