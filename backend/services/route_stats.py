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
    Convert route to detailed coordinates including street curvature.
    Extracts geometry from edges for smooth visualization.
    """
    coordinates = []
    
    for i in range(len(route_nodes) - 1):
        u, v = route_nodes[i], route_nodes[i+1]
        
        # Add start node
        if i == 0:
            coordinates.append({
                'lat': G.nodes[u]['y'],
                'lng': G.nodes[u]['x']
            })
        
        # Check if edge has detailed geometry
        if G.has_edge(u, v):
            edge_data = G.edges[u, v, 0]
            
            if 'geometry' in edge_data:
                # Edge has curved geometry
                geom = edge_data['geometry']
                for coord in geom.coords:
                    coordinates.append({
                        'lat': coord[1],  # latitude
                        'lng': coord[0]   # longitude
                    })
            else:
                # No geometry, just straight line to next node
                coordinates.append({
                    'lat': G.nodes[v]['y'],
                    'lng': G.nodes[v]['x']
                })
    
    return coordinates