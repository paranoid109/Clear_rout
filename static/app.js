document.addEventListener('DOMContentLoaded', () => {
    // State
    let startMarker = null;
    let endMarker = null;
    let fastestRouteLayer = null;
    let qualityRouteLayer = null;
    let selectedMode = 'car';
    let selectedCity = 'bengaluru';

    const cityCoords = {
        'bengaluru': [12.9716, 77.5946],
        'amsterdam': [52.3676, 4.9041]
    };

    // Initialize Map
    const map = L.map('map', {
        zoomControl: false,
        attributionControl: false
    }).setView(cityCoords[selectedCity], 13);

    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        maxZoom: 19
    }).addTo(map);

    L.control.zoom({ position: 'topright' }).addTo(map);

    // Elements
    const modeBtns = document.querySelectorAll('.mode-btn');
    const startInput = document.querySelector('#start-point input');
    const endInput = document.querySelector('#end-point input');
    const findRouteBtn = document.querySelector('#find-route-btn');
    const resPanel = document.querySelector('#results-panel');
    const cityAqi = document.querySelector('#city-aqi');
    const f1h = document.querySelector('#f-1h');
    const f3h = document.querySelector('#f-3h');
    const f1w = document.querySelector('#f-1w');
    const citySelector = document.querySelector('#city-selector');
    const loadingOverlay = document.getElementById('loading-overlay');
    const loadingText = document.getElementById('loading-text');

    // Loading Utils
    function showLoading(text) {
        loadingText.textContent = text || 'Loading...';
        loadingOverlay.classList.remove('hidden');
    }

    function hideLoading() {
        loadingOverlay.classList.add('hidden');
    }

    // City Selection
    citySelector.addEventListener('change', (e) => {
        selectedCity = e.target.value;
        map.setView(cityCoords[selectedCity], 13);
        
        // Clear UI
        if(startMarker) { map.removeLayer(startMarker); startMarker = null; }
        if(endMarker) { map.removeLayer(endMarker); endMarker = null; }
        if(fastestRouteLayer) { map.removeLayer(fastestRouteLayer); fastestRouteLayer = null; }
        if(qualityRouteLayer) { map.removeLayer(qualityRouteLayer); qualityRouteLayer = null; }
        startInput.value = '';
        endInput.value = '';
        resPanel.classList.add('hidden');
        findRouteBtn.disabled = true;
        
        updateCityStats();
    });

    // Stats Polling
    function updateCityStats() {
        fetch(`/stats?city=${selectedCity}`)
            .then(r => {
                if (!r.ok) {
                    // Demo mode may return error codes — don't let the UI get stuck
                    hideLoading();
                    console.warn(`Stats returned ${r.status} (demo edge case?)`);
                    return null;
                }
                return r.json();
            })
            .then(data => {
                if (!data) return; // Skipped due to error response above

                if (data.is_loading) {
                    showLoading(`Initializing ${selectedCity} map data...`);
                } else {
                    hideLoading();
                }

                if (cityAqi) cityAqi.textContent = Math.round(data.fused_aqi || 0);
                if (f1h) f1h.textContent = Math.round(data.forecast_1h || 0);
                if (f3h) f3h.textContent = Math.round(data.forecast_3h || 0);
                if (f1w) f1w.textContent = Math.round(data.forecast_1w || 0);
                
                const sourceBadge = document.querySelector('#data-source');
                if (sourceBadge) {
                    sourceBadge.textContent = data.data_source || 'Offline';
                    sourceBadge.style.background = data.data_source === 'LIVE' ? '#10b981' : '#f59e0b';
                }
            })
            .catch(err => {
                hideLoading(); // Never leave UI stuck on loading
                console.warn('Failed to fetch city stats:', err);
                
                // If it fails on init, try again shortly or hide overlay anyway
                setTimeout(hideLoading, 500);
            });
    }

    // Initial load + interval
    // Slight delay on start to ensure DOM and Leaflet are fully ready
    setTimeout(updateCityStats, 200);
    setInterval(updateCityStats, 15000);

    // Mode Selection
    modeBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            modeBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            selectedMode = btn.dataset.mode;
            if (startMarker && endMarker) calculateRoute();
        });
    });

    // Map Interaction
    map.on('click', (e) => {
        const { lat, lng } = e.latlng;

        if (!startMarker) {
            startMarker = L.marker([lat, lng], { draggable: true }).addTo(map);
            startInput.value = `${lat.toFixed(4)}, ${lng.toFixed(4)}`;
            startMarker.on('move', (ev) => {
                const p = ev.target.getLatLng();
                startInput.value = `${p.lat.toFixed(4)}, ${p.lng.toFixed(4)}`;
                checkReady();
            });
        } else if (!endMarker) {
            endMarker = L.marker([lat, lng], { 
                draggable: true,
                icon: L.icon({
                    iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-red.png',
                    shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png',
                    iconSize: [25, 41],
                    iconAnchor: [12, 41],
                    popupAnchor: [1, -34],
                    shadowSize: [41, 41]
                })
            }).addTo(map);
            endInput.value = `${lat.toFixed(4)}, ${lng.toFixed(4)}`;
            endMarker.on('move', (ev) => {
                const p = ev.target.getLatLng();
                endInput.value = `${p.lat.toFixed(4)}, ${p.lng.toFixed(4)}`;
                checkReady();
            });
        } else {
            // Already have both? Third click resets end marker
            map.removeLayer(endMarker);
            endMarker = L.marker([lat, lng], { 
                draggable: true,
                icon: L.icon({
                    iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-red.png',
                    shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png',
                    iconSize: [25, 41],
                    iconAnchor: [12, 41],
                    popupAnchor: [1, -34],
                    shadowSize: [41, 41]
                })
            }).addTo(map);
            endInput.value = `${lat.toFixed(4)}, ${lng.toFixed(4)}`;
        }
        checkReady();
    });

    function checkReady() {
        findRouteBtn.disabled = !(startMarker && endMarker);
    }

    findRouteBtn.addEventListener('click', calculateRoute);

    function calculateRoute() {
        if (!startMarker || !endMarker) return;

        const s = startMarker.getLatLng();
        const e = endMarker.getLatLng();

        showLoading('Calculating optimal paths...');
        findRouteBtn.disabled = true;

        fetch(`/route?start_lat=${s.lat}&start_lon=${s.lng}&end_lat=${e.lat}&end_lon=${e.lng}&mode=${selectedMode}&city=${selectedCity}`)
            .then(r => {
                if (!r.ok) throw new Error('Server returned error status');
                return r.json();
            })
            .then(data => {
                hideLoading();
                if (data.route_fastest && data.route_fastest.is_fallback) {
                    alert(`Routing Warning: ${data.route_fastest.error_message || "Points may be out of bounds."}`);
                }
                renderRoutes(data);
                updatePanel(data);
                findRouteBtn.disabled = false;
            })
            .catch(err => {
                hideLoading();
                console.error(err);
                alert(`Routing error: ${err.message}. Please try points within the city area.`);
                findRouteBtn.disabled = false;
            });
    }

    function renderRoutes(data) {
        if (!data.route_fastest || !data.route_quality) return;
        
        if (fastestRouteLayer) map.removeLayer(fastestRouteLayer);
        if (qualityRouteLayer) map.removeLayer(qualityRouteLayer);

        qualityRouteLayer = L.polyline(data.route_quality.path, {
            color: '#10b981',
            weight: 6,
            opacity: 0.8,
            lineJoin: 'round'
        }).addTo(map);

        fastestRouteLayer = L.polyline(data.route_fastest.path, {
            color: '#3b82f6',
            weight: 4,
            opacity: 0.8,
            dashArray: data.worth_it ? '10, 10' : ''
        }).addTo(map);

        const bounds = L.latLngBounds(data.route_fastest.path);
        map.fitBounds(bounds, { padding: [50, 50] });
    }

    function updatePanel(data) {
        if (!resPanel) return;
        resPanel.classList.remove('hidden');
        
        const setVal = (id, val) => {
            const el = document.getElementById(id);
            if (el) el.textContent = val;
        };

        if (data.route_fastest) {
            setVal('res-time-fast', `${Math.round(data.route_fastest.time_min)} min`);
            setVal('res-aqi-fast', Math.round(data.route_fastest.aqi_mean));
        }
        
        if (data.route_quality) {
            setVal('res-time-clean', `${Math.round(data.route_quality.time_min)} min`);
            setVal('res-aqi-clean', Math.round(data.route_quality.aqi_mean));
        }
        
        setVal('res-reason', data.worth_it_reason || 'No specific insights.');

        const box = document.getElementById('recommendation');
        if (box) {
            if (data.worth_it) {
                box.style.background = 'rgba(16, 185, 129, 0.1)';
                box.style.borderColor = '#10b981';
            } else {
                box.style.background = 'rgba(255, 255, 255, 0.05)';
                box.style.borderColor = 'rgba(255, 255, 255, 0.1)';
            }
        }
    }
});
