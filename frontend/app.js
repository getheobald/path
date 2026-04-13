// Initialize map centered on Boston
// Last param controls zoom
// N = higher lat, S = lower lat, E = lower lon, W = higher long
// Latitutde is first, longitude is second
const map = L.map('map').setView([42.3510, -71.0790], 13);

// Add OpenStreetMap tiles
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap contributors',
    maxZoom: 19
}).addTo(map);

// State variables
let startMarker = null;
let startLocation = null;
let routeLine = null;

// Handle map clicks to set starting point
map.on('click', async function(e) {
    const { lat, lng } = e.latlng;
    
    // Remove previous marker if exists
    if (startMarker) {
        map.removeLayer(startMarker);
    }

    const tempMarker = L.marker([lat, lng], {opacity: 0.5}).addTo(map);

    try {
        // Ask backend to find nearest valid road node
        const response = await fetch('http://localhost:5000/api/nearest-node', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({lat, lng, network: document.getElementById('network').value})
        });
        
        if (!response.ok) {
            throw new Error('No nearby roads found');
        }
        
        const data = await response.json();
        
        // Remove temp marker
        map.removeLayer(tempMarker);
        
        // Place marker at actual road location (snapped)
        startMarker = L.marker([data.lat, data.lng]).addTo(map)
            .bindPopup('START', {
                closeButton: false,
                className: 'start-popup'
            })
            .openPopup();
        
        // Store the snapped location
        startLocation = {lat: data.lat, lng: data.lng};
        
        // Update UI
        document.getElementById('start-coords').textContent = 
            `${data.lat.toFixed(4)}, ${data.lng.toFixed(4)}`;
        document.getElementById('generate-btn').disabled = false;
        
        // Hide previous results
        document.getElementById('result-info').style.display = 'none';
        document.getElementById('error-message').style.display = 'none';
        
        // Remove previous route
        if (routeLine) {
            map.removeLayer(routeLine);
            routeLine = null;
        }
        
    } catch (error) {
        map.removeLayer(tempMarker);
        showError('Please click on a road. The selected location is not accessible.');
    }
});

async function generateRoute() {
    const distance = parseFloat(document.getElementById('distance').value);
    const elevation = document.getElementById('elevation').value;
    
    // Validate
    if (!startLocation) {
        showError('Please click on the map to set a starting location');
        return;
    }
    
    if (!distance || distance < 1 || distance > 50) {
        showError('Please enter a distance between 1 and 50 km');
        return;
    }
    
    // Show loading state
    const button = document.getElementById('generate-btn');
    const originalText = button.textContent;
    button.textContent = 'Generating...';
    button.disabled = true;
    
    try {
        // Call backend API
        const response = await fetch('http://localhost:5000/api/generate-route', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                start: startLocation,
                distance: distance,
                elevation: elevation,
                greenery: document.getElementById('greenery').value,
                network: document.getElementById('network').value,
            })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to generate route');
        }
        
        const data = await response.json();
        
        // Display route
        displayRoute(data);
        
        // Show results
        showResults(data);
        
        // Hide errors
        document.getElementById('error-message').style.display = 'none';
        
    } catch (error) {
        console.error('Error:', error);
        showError(error.message || 'Failed to generate route. Make sure the backend server is running.');
    } finally {
        // Re-enable button
        button.textContent = originalText;
        button.disabled = false;
    }
}

function displayRoute(data) {
    // Remove previous route
    if (routeLine) {
        map.removeLayer(routeLine);
    }
    
    // Convert to Leaflet format
    const latlngs = data.route.map(point => [point.lat, point.lng]);
    
    // Draw route
    routeLine = L.polyline(latlngs, {
        color: '#3498db',
        weight: 6,
        opacity: 0.8
    }).addTo(map);
    
    // Fit map to show entire route
    map.fitBounds(routeLine.getBounds(), { padding: [50, 50] });
}

function showResults(data) {
    document.getElementById('result-distance').textContent = 
        data.distance.toFixed(2);
    document.getElementById('result-elevation').textContent = 
        data.elevation_gain.toFixed(0);
    document.getElementById('result-elevation-loss').textContent = 
        data.elevation_loss.toFixed(0);
    document.getElementById('result-info').style.display = 'block';
}

function showError(message) {
    const errorDiv = document.getElementById('error-message');
    errorDiv.textContent = message;
    errorDiv.style.display = 'block';
}

// Test backend connection on load
window.addEventListener('load', async () => {
    try {
        const response = await fetch('http://localhost:5000/api/health');
        if (response.ok) {
            const data = await response.json();
            console.log('Backend connected:', data);
        }
    } catch (error) {
        console.warn('Backend not running. Start it with: cd backend && python app.py');
    }
});