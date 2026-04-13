def calculate_route_stats(G, route_nodes):
    """
    Calculate statistics for a route.
    
    Args:
        G: OSMnx graph
        route_nodes: List of node IDs
        
    Returns:
        Dict with distance, elevation_gain, elevation_loss
    """
    if not route_nodes or len(route_nodes) < 2:
        return {
            'distance_km': 0,
            'elevation_gain_m': 0,
            'elevation_loss_m': 0
        }
    
    total_distance = 0
    elevation_gain = 0
    elevation_loss = 0
    
    for i in range(len(route_nodes) - 1):
        u, v = route_nodes[i], route_nodes[i+1]
        
        # Get edge length
        if G.has_edge(u, v):
            edge_data = G.edges[u, v, 0]
            total_distance += edge_data.get('length', 0)
        
        # Calculate elevation change
        if 'elevation' in G.nodes[u] and 'elevation' in G.nodes[v]:
            elev_change = G.nodes[v]['elevation'] - G.nodes[u]['elevation']
            if elev_change > 0:
                elevation_gain += elev_change
            else:
                elevation_loss += abs(elev_change)
    
    return {
        'distance_km': total_distance / 1000,
        'elevation_gain_m': elevation_gain,
        'elevation_loss_m': elevation_loss
    }

def route_nodes_to_coordinates(G, route_nodes):
    """
    Convert list of node IDs to lat/lng coordinates, including elevation
    and the greenery_score of the outgoing edge for each node.

    Returns:
        List of {'lat', 'lng', 'elevation', 'greenery_score'} dicts
    """
    coordinates = []

    for i, node_id in enumerate(route_nodes):
        node_data = G.nodes[node_id]

        elevation = node_data.get('elevation')

        # Both street_name and greenery_score come from the incoming edge
        greenery_score = 0.0
        street_name = None
        if i > 0:
            prev = route_nodes[i - 1]
            if G.has_edge(prev, node_id):
                edge_data = G.edges[prev, node_id, 0]
                greenery_score = edge_data.get('greenery_score', 0.0)
                name = edge_data.get('name')
                if isinstance(name, list):
                    name = name[0] if name else None
                street_name = name

        coordinates.append({
            'lat': node_data['y'],
            'lng': node_data['x'],
            'elevation': elevation,
            'greenery_score': greenery_score,
            'street_name': street_name
        })

    return coordinates