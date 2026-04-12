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

def calculate_fitness(G, route_waypoints, target_distance_km, elevation_pref='flat', greenery_pref='medium'):
    """
    Calculate fitness score for a route
    Higher score = better route.

    Priorities:
    1. Must match distance
    2. Should match elevation preference
    3. Should match greenery preference
    4. Penalize busy/unsafe roads
    5. Penalize backtracking/repeated edges
    6. Loop quality

    """

    #print(f"  Calculating fitness for {len(route_waypoints)} waypoints...")
    
    full_route = build_full_route(G, route_waypoints)
    #print(f"  Built route with {len(full_route) if full_route else 0} nodes")
    
    # invalid route which is obviously very bad
    if not full_route or len(full_route) < 2:
        return -100000
    
    # DISTANCE SCORE
    total_distance = 0
    for i in range(len(full_route) - 1):
        u, v = full_route[i], full_route[i+1]
        if G.has_edge(u, v):
            total_distance += G.edges[u, v, 0].get('length', 0)
    
    actual_distance_km = total_distance / 1000
    distance_error = abs(actual_distance_km - target_distance_km)
    
    # heavy penalty for distance errors
    # i.e. if we want 5km and get 3km, that's 2km error = -1000 points
    distance_score = 1000 - (distance_error * 1000)
    
    # ELEVATION SCORE
    elevation_score = 0
    if 'elevation' in G.nodes[full_route[0]]:
        elevation_gain = calculate_elevation_gain(G, full_route)
        
        if elevation_pref == 'flat':
            # penalize any elevation gain
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
                # too hilly
                elevation_score = -(elevation_gain - 400) * 0.3
                
        elif elevation_pref == 'very-hilly':
            # reward high elevation
            # more is better, to a point
            if elevation_gain < 200:
                elevation_score = -100
            else:
                elevation_score = min(elevation_gain * 0.4, 300)  # cap at 300 points

    greenery_score = calculate_greenery_score(G, full_route, greenery_pref)

    backtracking_penalty = calculate_backtracking(full_route)

    # weight_by_road_type already handles highways in pathfinding, but this is a small backup penalty
    busyness_penalty = calculate_road_busyness_penalty(G, full_route)
    
    # LOOP QUALITY
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
    total_score = distance_score + elevation_score + loop_score + greenery_score - backtracking_penalty - busyness_penalty
    
    return total_score

def build_full_route(G, waypoints):
    """
    Build full route through waypoints using shortest paths.
    Uses weight_by_road_type to avoid highways and busy roads.
    
    Returns:
        List of node IDs forming complete route
    """
    full_route = []
    
    for i in range(len(waypoints) - 1):
        try:
            # Find shortest path between consecutive waypoints
            # segment = ox.shortest_path(G, waypoints[i], waypoints[i+1], weight=weight_by_road_type)
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

def calculate_backtracking(route_nodes):
    """
    Penalize routes that revisit nodes or use same edges multiple times.
    """
    # Count repeated nodes (excluding start/end which should repeat)
    unique_nodes = set(route_nodes[1:-1])  # Exclude start and end
    total_nodes = len(route_nodes[1:-1])
    
    if total_nodes == 0:
        return 0
    
    # If we visit 100 nodes but only 80 are unique, we backtracked through 20
    repeated_nodes = total_nodes - len(unique_nodes)
    
    # Penalize: each repeated node = -50 points
    node_penalty = repeated_nodes * 20
    
    # Also check for repeated edges (going down same street twice)
    edge_list = []
    repeated_edges = 0
    
    for i in range(len(route_nodes) - 1):
        edge = (min(route_nodes[i], route_nodes[i+1]), 
                max(route_nodes[i], route_nodes[i+1]))  # Undirected edge
        
        if edge in edge_list:
            repeated_edges += 1
        edge_list.append(edge)
    
    # Each repeated edge = -100 points (more severe)
    edge_penalty = repeated_edges * 40
    
    total_penalty = node_penalty + edge_penalty
    
    return total_penalty

def calculate_road_busyness_penalty(G, route_nodes):
    """
    Penalize routes that use busy/major roads.
    Backup penalty in case highways slip through pathfinding.
    """
    penalty = 0
    
    for i in range(len(route_nodes) - 1):
        u, v = route_nodes[i], route_nodes[i+1]
        
        if G.has_edge(u, v):
            edge_data = G.edges[u, v, 0]
            highway_type = edge_data.get('highway', 'unclassified')
            
            if isinstance(highway_type, list):
                highway_type = highway_type[0]
            
            # Severe penalties for highways (backup to pathfinding filter)
            if highway_type in ['motorway', 'motorway_link', 'trunk', 'trunk_link']:
                penalty += 1000  # Should never happen, but just in case
            elif highway_type in ['primary', 'primary_link']:
                penalty += 200   # Major roads
            elif highway_type in ['secondary', 'secondary_link']:
                penalty += 100   # Busy roads
            elif highway_type in ['tertiary', 'tertiary_link']:
                penalty += 30
            elif highway_type in ['residential', 'living_street']:
                penalty += 0
            elif highway_type in ['path', 'footway', 'cycleway', 'track', 'pedestrian']:
                penalty -= 50    # Reward these paths!!!
            elif highway_type in ['service', 'unclassified']:
                penalty += 20
    
    return penalty

def weight_by_road_type(u, v, d):
    """
    Custom weight function for pathfinding that avoids dangerous/busy roads.
    
    Makes highways extremely expensive so shortest_path avoids them.
    Returns effective "cost" of using this edge.
    
    Args:
        u, v: nodes (from OSMnx)
        d: edge data dictionary
        
    Returns:
        Weighted cost (higher = avoid this edge)
    """
    length = d[0].get('length', 1)
    highway_type = d[0].get('highway', 'unclassified')
    
    # Handle if highway is a list (some edges have multiple types)
    if isinstance(highway_type, list):
        highway_type = highway_type[0]
    
    # Weight multipliers based on road type
    if highway_type in ['motorway', 'motorway_link', 'trunk', 'trunk_link']:
        return length * 10000  # Highways - effectively impossible
    elif highway_type in ['primary', 'primary_link']:
        return length * 50     # Major roads (Storrow Drive) - avoid
    elif highway_type in ['secondary', 'secondary_link']:
        return length * 5      # Busy roads - discourage
    elif highway_type in ['tertiary', 'tertiary_link']:
        return length * 2      # Moderate traffic
    else:
        return length          # Residential, paths, etc - normal cost
    
def calculate_greenery_score(G, full_route, greenery_pref='medium'):
    """
    Calculate greenery score based on route's proximity to parks.
    """
    scores = []
    for i in range(len(full_route) - 1):
        u, v = full_route[i], full_route[i+1]
        if G.has_edge(u, v):
            scores.append(G[u][v][0].get('greenery_score', 0))
    
    if not scores:
        return 0
    
    avg = sum(scores) / len(scores)

    if greenery_pref == 'low':
        if avg <= 0.2:
            return 200  # Reduced from 500
        else:
            return -((avg - 0.2) / 0.8) * 100
    elif greenery_pref == 'medium':
        return 0  # Neutral
    elif greenery_pref == 'high':
        if avg >= 0.6:
            return 200  # Reduced from 500
        else:
            return -((1 - (avg / 0.6)) * 100)
    
    return 0