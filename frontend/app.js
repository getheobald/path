// Initialize map centered on Boston
// Last param controls zoom
// N = higher lat, S = lower lat, E = lower lon, W = higher long
// Latitutde is first, longitude is second
const map = L.map('map').setView([42.3510, -71.0790], 13);

// Set running man emoji as the map cursor (injected as a style rule so it
// overrides Leaflet's own cursor: grab on .leaflet-container and children)
(function() {
    const canvas = document.createElement('canvas');
    canvas.width = 32;
    canvas.height = 32;
    const ctx = canvas.getContext('2d');
    ctx.font = '26px serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    // Build up a solid black outline using shadow, then draw clean on top
    ctx.shadowColor = 'black';
    ctx.shadowBlur = 3;
    for (let i = 0; i < 4; i++) ctx.fillText('🏃', 16, 16);
    ctx.shadowBlur = 0;
    ctx.fillText('🏃', 16, 16);
    const cur = `url('${canvas.toDataURL()}') 16 16, auto`;
    const style = document.createElement('style');
    style.textContent = `#map, #map * { cursor: ${cur} !important; }`;
    document.head.appendChild(style);
})();

// Add OpenStreetMap tiles
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap contributors',
    maxZoom: 19
}).addTo(map);

// Custom fit-to controls (top-left, below zoom buttons)
const FitControls = L.Control.extend({
    options: { position: 'topleft' },
    onAdd() {
        const container = L.DomUtil.create('div', 'leaflet-bar leaflet-control');
        L.DomEvent.disableClickPropagation(container);

        const fitAreaBtn = L.DomUtil.create('a', 'fit-btn', container);
        fitAreaBtn.textContent = 'Fit to Area';
        fitAreaBtn.title = 'Zoom to network boundary';
        fitAreaBtn.href = '#';
        L.DomEvent.on(fitAreaBtn, 'click', e => { L.DomEvent.preventDefault(e); fitToArea(); });

        const fitRouteBtn = L.DomUtil.create('a', 'fit-btn fit-btn-disabled', container);
        fitRouteBtn.id = 'fit-route-btn';
        fitRouteBtn.textContent = 'Fit to Route';
        fitRouteBtn.title = 'Zoom to current route';
        fitRouteBtn.href = '#';
        L.DomEvent.on(fitRouteBtn, 'click', e => { L.DomEvent.preventDefault(e); fitToRoute(); });

        return container;
    }
});
new FitControls().addTo(map);

function fitToArea() {
    if (networkBoundsLayer) {
        map.fitBounds(networkBoundsLayer.getBounds(), { padding: [20, 20] });
    }
}

function fitToRoute() {
    if (routeLine) {
        map.fitBounds(routeLine.getBounds(), { padding: [50, 50] });
    }
}

// Distance slider <-> number input sync
const distanceInput = document.getElementById('distance');
const distanceSlider = document.getElementById('distance-slider');
distanceSlider.addEventListener('input', function() {
    distanceInput.value = this.value;
});
distanceInput.addEventListener('input', function() {
    distanceSlider.value = Math.min(parseFloat(this.value) || 0, 25);
});

// Elevation slider label
const elevationLabels = { '1': 'Flat', '2': 'Hilly', '3': 'Very Hilly' };
const elevationValues = { '1': 'flat', '2': 'hilly', '3': 'very-hilly' };
document.getElementById('elevation').addEventListener('input', function() {
    document.getElementById('elevation-label').textContent = elevationLabels[this.value];
});

// Nature preference slider label
const greeneryLabels = { '1': 'Low', '2': 'Medium', '3': 'High' };
const greeneryValues = { '1': 'low', '2': 'medium', '3': 'high' };
document.getElementById('greenery').addEventListener('input', function() {
    document.getElementById('greenery-label').textContent = greeneryLabels[this.value];
});

// State variables
let startMarker = null;       // pending start pin (placed on click)
let completedMarker = null;   // pin shown after route generation
let startLocation = null;
let routeLine = null;
let routeMarkers = [];        // emoji markers along the route
let networkBoundsLayer = null;

// --- Address search (Nominatim) ---

async function reverseGeocode(lat, lng) {
    const input = document.getElementById('address-input');
    input.value = 'Looking up address…';
    try {
        const res = await fetch(
            `https://nominatim.openstreetmap.org/reverse?lat=${lat}&lon=${lng}&format=json`,
            { headers: { 'Accept-Language': 'en' } }
        );
        const data = await res.json();
        input.value = data.display_name ?? '';
    } catch {
        input.value = '';
    }
}

let _addrDebounce = null;
document.getElementById('address-input').addEventListener('input', function () {
    clearTimeout(_addrDebounce);
    const q = this.value.trim();
    if (q.length < 3) { closeSuggestions(); return; }
    _addrDebounce = setTimeout(() => fetchSuggestions(q), 400);
});

async function fetchSuggestions(query) {
    try {
        const res = await fetch(
            `https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(query)}&format=json&limit=5`,
            { headers: { 'Accept-Language': 'en' } }
        );
        const results = await res.json();
        renderSuggestions(results);
    } catch {
        closeSuggestions();
    }
}

function renderSuggestions(results) {
    const box = document.getElementById('address-suggestions');
    box.innerHTML = '';
    if (!results.length) { closeSuggestions(); return; }
    results.forEach(r => {
        const item = document.createElement('div');
        item.className = 'address-suggestion-item';
        item.textContent = r.display_name;
        item.addEventListener('mousedown', e => {
            e.preventDefault(); // keep focus so blur doesn't fire first
            selectAddress(r);
        });
        box.appendChild(item);
    });
    box.style.display = 'block';
}

function closeSuggestions() {
    document.getElementById('address-suggestions').style.display = 'none';
}

document.getElementById('address-input').addEventListener('blur', closeSuggestions);

function selectAddress(result) {
    const lat = parseFloat(result.lat);
    const lng = parseFloat(result.lon);

    document.getElementById('address-input').value = result.display_name;
    closeSuggestions();

    // Place marker exactly as a map click would
    if (startMarker) map.removeLayer(startMarker);
    startMarker = L.marker([lat, lng]).addTo(map)
        .bindPopup('START', { closeButton: false, className: 'start-popup' })
        .openPopup();

    startLocation = { lat, lng };
    document.getElementById('start-coords').textContent =
        `${lat.toFixed(4)}, ${lng.toFixed(4)}`;
    document.getElementById('generate-btn').disabled = false;
    document.getElementById('error-message').style.display = 'none';

    map.setView([lat, lng], 15);
}

// Handle map clicks to set starting point
map.on('click', async function(e) {
    const { lat, lng } = e.latlng;

    if (startMarker) map.removeLayer(startMarker);
    document.getElementById('error-message').style.display = 'none';
    reverseGeocode(lat, lng);

    // Try to snap to the nearest road node; fall back to the raw click if it fails
    let snapLat = lat, snapLng = lng;
    try {
        const response = await fetch('http://localhost:5000/api/nearest-node', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({lat, lng, network: document.getElementById('network').value})
        });
        if (response.ok) {
            const data = await response.json();
            snapLat = data.lat;
            snapLng = data.lng;
        }
    } catch {}

    startMarker = L.marker([snapLat, snapLng]).addTo(map)
        .bindPopup('START', { closeButton: false, className: 'start-popup' })
        .openPopup();

    startLocation = { lat: snapLat, lng: snapLng };
    document.getElementById('start-coords').textContent =
        `${snapLat.toFixed(4)}, ${snapLng.toFixed(4)}`;
    document.getElementById('generate-btn').disabled = false;
});

async function generateRoute() {
    const distance = parseFloat(document.getElementById('distance').value);
    const elevation = elevationValues[document.getElementById('elevation').value];
    const greenery = greeneryValues[document.getElementById('greenery').value];
    
    // Validate
    if (!startLocation) {
        showError('Please click on the map to set a starting location');
        return;
    }
    
    if (!distance || distance < 1 || distance > 50) {
        showError('Please enter a distance between 1 and 50 km');
        return;
    }
    
    // Clear previous completed marker, route markers, and route line
    if (completedMarker) { map.removeLayer(completedMarker); completedMarker = null; }
    routeMarkers.forEach(m => map.removeLayer(m));
    routeMarkers = [];
    if (routeLine) { map.removeLayer(routeLine); routeLine = null; }

    // If user re-generates without clicking a new location, re-place the start pin
    if (!startMarker && startLocation) {
        startMarker = L.marker([startLocation.lat, startLocation.lng]).addTo(map)
            .bindPopup('START', { closeButton: false, className: 'start-popup' })
            .openPopup();
    }

    document.getElementById('result-info').style.display = 'none';
    document.getElementById('directions-info').style.display = 'none';
    const fitRouteBtn = document.getElementById('fit-route-btn');
    if (fitRouteBtn) fitRouteBtn.classList.add('fit-btn-disabled');

    // Show loading state
    const button = document.getElementById('generate-btn');
    const originalText = button.textContent;
    button.textContent = 'Generating...';
    button.disabled = true;

    // Show and reset progress bar
    const progressContainer = document.getElementById('progress-container');
    const progressBar = document.getElementById('progress-bar');
    progressBar.style.width = '0%';
    progressContainer.style.display = 'block';

    // Poll backend for real iteration progress every 150 ms
    const pollInterval = setInterval(async () => {
        try {
            const res = await fetch('http://localhost:5000/api/progress');
            const prog = await res.json();
            if (prog.total > 0) {
                progressBar.style.width = `${(prog.current / prog.total) * 100}%`;
            }
        } catch {}
    }, 150);

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
                greenery: greenery,
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

        // Show results and directions
        showResults(data);
        showDirections(data.route);
        
        // Hide errors
        document.getElementById('error-message').style.display = 'none';
        
    } catch (error) {
        console.error('Error:', error);
        showError(error.message || 'Failed to generate route. Make sure the backend server is running.');
    } finally {
        clearInterval(pollInterval);
        progressBar.style.width = '100%';
        setTimeout(() => { progressContainer.style.display = 'none'; }, 400);
        // Re-enable button
        button.textContent = originalText;
        button.disabled = false;
    }
}

function makeEmojiMarker(lat, lng, emoji) {
    return L.marker([lat, lng], {
        icon: L.divIcon({
            className: '',
            html: `<span style="font-size:18px;line-height:1;filter:drop-shadow(0 0 2px rgba(0,0,0,0.6));">${emoji}</span>`,
            iconSize: [22, 22],
            iconAnchor: [11, 11]
        }),
        interactive: false
    });
}

function displayRoute(data) {
    // Remove previous route
    if (routeLine) {
        map.removeLayer(routeLine);
    }

    // Convert to Leaflet format
    const latlngs = data.route.map(point => [point.lat, point.lng]);

    // Draw route in red
    routeLine = L.polyline(latlngs, {
        color: '#e74c3c',
        weight: 6,
        opacity: 0.8
    }).addTo(map);
    
    // Auto-zoom to route and enable the fit-route button
    map.fitBounds(routeLine.getBounds(), { padding: [50, 50] });
    const fitRouteBtn = document.getElementById('fit-route-btn');
    if (fitRouteBtn) fitRouteBtn.classList.remove('fit-btn-disabled');

    // Place emoji markers along the route
    const coords = data.route;
    const GREEN_THRESHOLD = 0.5;
    const ELEV_THRESHOLD = 10; // metres

    for (let i = 1; i < coords.length; i++) {
        const cur  = coords[i];
        const prev = coords[i - 1];

        // ⛰️  elevation change ≥ 10 m
        if (cur.elevation != null && prev.elevation != null &&
            Math.abs(cur.elevation - prev.elevation) >= ELEV_THRESHOLD) {
            routeMarkers.push(makeEmojiMarker(cur.lat, cur.lng, '⛰️').addTo(map));
        }

        // 🌳  first transition from non-green to green
        if (prev.greenery_score < GREEN_THRESHOLD && cur.greenery_score >= GREEN_THRESHOLD) {
            routeMarkers.push(makeEmojiMarker(cur.lat, cur.lng, '🌳').addTo(map));
        }
    }

    // Transfer pending marker → completed marker and update its popup
    if (startMarker) {
        completedMarker = startMarker;
        startMarker = null;
        completedMarker.setIcon(L.divIcon({
            className: '',
            html: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 25 41" width="25" height="41"><path fill="#27ae60" stroke="#1e8449" stroke-width="1" d="M12.5 0C5.6 0 0 5.6 0 12.5c0 9.4 12.5 28.5 12.5 28.5S25 21.9 25 12.5C25 5.6 19.4 0 12.5 0z"/><circle fill="white" cx="12.5" cy="12.5" r="4.5"/></svg>',
            iconSize: [25, 41],
            iconAnchor: [12, 41],
            popupAnchor: [1, -34]
        }));
        const estMin = Math.round((data.distance / 5) * 60);
        const elevClimbedStr = data.elevation_gain != null ? `${Math.round(data.elevation_gain)} m` : 'N/A';
        completedMarker.unbindPopup();
        completedMarker
            .bindPopup(
                `<div class="completed-popup-inner">
                    <strong>&#10003; Completed!</strong><br>
                    Est. Time: ${estMin} min<br>
                    Route Distance: ${data.distance.toFixed(2)} km<br>
                    Elevation Climbed: ${elevClimbedStr}
                </div>`,
                { closeButton: false, className: 'completed-popup' }
            )
            .openPopup();
    }
}

function showResults(data) {
    document.getElementById('result-distance').textContent = 
        data.distance.toFixed(2);
    document.getElementById('result-elevation').textContent =
        data.elevation_gain.toFixed(0);
    document.getElementById('result-info').style.display = 'block';
}

function showError(message) {
    const errorDiv = document.getElementById('error-message');
    errorDiv.textContent = message;
    errorDiv.style.display = 'block';
}

// --- Street-level turn-by-turn directions ---

function calcBearing(lat1, lng1, lat2, lng2) {
    const r = Math.PI / 180;
    const dLng = (lng2 - lng1) * r;
    const y = Math.sin(dLng) * Math.cos(lat2 * r);
    const x = Math.cos(lat1 * r) * Math.sin(lat2 * r) -
              Math.sin(lat1 * r) * Math.cos(lat2 * r) * Math.cos(dLng);
    return (Math.atan2(y, x) * 180 / Math.PI + 360) % 360;
}

function haversineDist(lat1, lng1, lat2, lng2) {
    const R = 6371000, r = Math.PI / 180;
    const dLat = (lat2 - lat1) * r, dLng = (lng2 - lng1) * r;
    const a = Math.sin(dLat / 2) ** 2 +
              Math.cos(lat1 * r) * Math.cos(lat2 * r) * Math.sin(dLng / 2) ** 2;
    return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

function bearingToCardinalFull(b) {
    return ['north','northeast','east','southeast','south','southwest','west','northwest']
        [Math.round(b / 45) % 8];
}

function formatDist(m) {
    return m >= 1000 ? `${(m / 1000).toFixed(1)} km` : `${Math.round(m)} m`;
}

function formatStreet(name) {
    if (!name) return 'unnamed road';
    return Array.isArray(name) ? name[0] : name;
}

function turnDetails(angle) {
    const a = Math.abs(angle);
    if (a > 135) return { text: 'Make a U-turn',        icon: '↩' };
    if (angle > 45)  return { text: 'Turn right',           icon: '→' };
    if (angle > 15)  return { text: 'Turn slight right',    icon: '↗' };
    if (angle > -15) return { text: 'Continue straight',    icon: '↑' };
    if (angle > -45) return { text: 'Turn slight left',     icon: '↖' };
    return              { text: 'Turn left',            icon: '←' };
}

function generateStreetDirections(route) {
    if (!route || route.length < 2) return [];

    const steps = [];
    const initBearing = calcBearing(route[0].lat, route[0].lng, route[1].lat, route[1].lng);

    steps.push({
        icon: '↑',
        text: `Head ${bearingToCardinalFull(initBearing)} on ${formatStreet(route[1].street_name)}`,
        distance: 0
    });

    let segDist = 0;

    for (let i = 1; i < route.length - 1; i++) {
        segDist += haversineDist(route[i - 1].lat, route[i - 1].lng, route[i].lat, route[i].lng);

        const curStreet  = route[i].street_name;
        const nextStreet = route[i + 1].street_name;

        if (curStreet !== nextStreet && (curStreet || nextStreet)) {
            steps[steps.length - 1].distance = segDist;

            const b1 = calcBearing(route[i - 1].lat, route[i - 1].lng, route[i].lat, route[i].lng);
            const b2 = calcBearing(route[i].lat, route[i].lng, route[i + 1].lat, route[i + 1].lng);
            const angle = ((b2 - b1 + 540) % 360) - 180;
            const td = turnDetails(angle);

            steps.push({
                icon: td.icon,
                text: `${td.text} onto ${formatStreet(nextStreet)}`,
                distance: 0
            });
            segDist = 0;
        }
    }

    // Distance for the last moving step
    segDist += haversineDist(
        route[route.length - 2].lat, route[route.length - 2].lng,
        route[route.length - 1].lat, route[route.length - 1].lng
    );
    steps[steps.length - 1].distance = segDist;

    steps.push({ icon: '🏁', text: 'You have arrived at your destination', distance: null });

    return steps;
}

function showDirections(route) {
    const steps = generateStreetDirections(route);
    const list = document.getElementById('directions-list');
    list.innerHTML = '';

    steps.forEach(step => {
        const el = document.createElement('div');
        el.className = 'direction-step';
        el.innerHTML = `
            <div class="direction-icon">${step.icon}</div>
            <div class="direction-text">
                ${step.text}
                ${step.distance != null ? `<div class="direction-distance">${formatDist(step.distance)}</div>` : ''}
            </div>`;
        list.appendChild(el);
    });

    document.getElementById('directions-info').style.display = 'block';
}

async function loadNetworkBounds() {
    try {
        const response = await fetch('http://localhost:5000/api/network-bounds');
        if (!response.ok) return;
        const data = await response.json();

        const outlineStyle = {
            color: '#2980b9',
            weight: 4,
            opacity: 0.8,
            fillOpacity: 0
        };

        if (data.geojson) {
            networkBoundsLayer = L.geoJSON(data.geojson, { style: outlineStyle }).addTo(map);
        } else if (data.bbox) {
            networkBoundsLayer = L.polygon(data.bbox, outlineStyle).addTo(map);
        }
    } catch (error) {
        console.warn('Could not load network bounds:', error);
    }
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

    loadNetworkBounds();
});