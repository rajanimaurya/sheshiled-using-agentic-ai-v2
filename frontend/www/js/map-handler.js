/* =====================================================
   SheShield — Map Integration Module
   
   Features:
   - Display user location on map
   - Show nearby places (hospital, police, restaurant, mall)
   - Route directions using Google Maps
   - SOS trigger with map display
   ===================================================== */

class SheShieldMapHandler {
    constructor() {
        this.map = null;
        this.userMarker = null;
        this.nearbyMarkers = [];
        this.userLocation = null;
        this.API_KEY = 'YOUR_GOOGLE_MAPS_API_KEY'; // Replace with actual key
    }

    /**
     * Initialize Google Map
     */
    initMap(containerId, latitude, longitude, zoom = 15) {
        const location = { lat: latitude, lng: longitude };
        this.userLocation = location;

        this.map = new google.maps.Map(document.getElementById(containerId), {
            zoom: zoom,
            center: location,
            mapTypeControl: true,
            fullscreenControl: true,
            streetViewControl: true,
            zoomControl: true,
        });

        // Add user location marker
        this.addUserMarker(latitude, longitude);

        return this.map;
    }

    /**
     * Add marker for user's current location
     */
    addUserMarker(latitude, longitude) {
        if (this.userMarker) {
            this.userMarker.setMap(null);
        }

        this.userMarker = new google.maps.Marker({
            position: { lat: latitude, lng: longitude },
            map: this.map,
            title: 'Your Current Location',
            icon: 'http://maps.google.com/mapfiles/ms/icons/blue-dot.png',
        });

        const infoWindow = new google.maps.InfoWindow({
            content: '<div><strong>Your Location</strong><br>Lat: ' + latitude.toFixed(4) + '<br>Lng: ' + longitude.toFixed(4) + '</div>',
        });

        this.userMarker.addListener('click', () => {
            infoWindow.open(this.map, this.userMarker);
        });
    }

    /**
     * Add markers for nearby places
     */
    addNearbyPlaces(places) {
        // Clear existing markers
        this.nearbyMarkers.forEach(marker => marker.setMap(null));
        this.nearbyMarkers = [];

        const icons = {
            hospital: 'http://maps.google.com/mapfiles/ms/icons/hospital.png',
            police: 'http://maps.google.com/mapfiles/ms/icons/police.png',
            mall: 'http://maps.google.com/mapfiles/ms/icons/shopping.png',
            restaurant: 'http://maps.google.com/mapfiles/ms/icons/restaurant.png',
        };

        places.forEach(place => {
            const marker = new google.maps.Marker({
                position: { lat: place.lat, lng: place.lng },
                map: this.map,
                title: place.name,
                icon: icons[place.type?.toLowerCase()] || 'http://maps.google.com/mapfiles/ms/icons/red-dot.png',
            });

            const infoContent = `
                <div style="font-family: Arial; width: 220px;">
                    <strong>${place.name}</strong><br>
                    <small style="color: #666;">${place.type}</small><br>
                    <small style="color: #999;">📏 ${place.distance}m away</small><br>
                    <small style="color: #888;">📍 ${place.address}</small><br>
                    <a href="https://www.google.com/maps?q=${place.lat},${place.lng}" target="_blank" style="color: #007AFF; text-decoration: none;">View on Maps →</a>
                </div>
            `;

            const infoWindow = new google.maps.InfoWindow({
                content: infoContent,
            });

            marker.addListener('click', () => {
                // Close all other info windows
                this.nearbyMarkers.forEach(m => {
                    if (m.infoWindow) m.infoWindow.close();
                });
                infoWindow.open(this.map, marker);
                marker.infoWindow = infoWindow;
            });

            marker.infoWindow = infoWindow;
            this.nearbyMarkers.push(marker);
        });

        // Adjust map to fit all markers
        this.fitMapToMarkers();
    }

    /**
     * Fit map to show all markers
     */
    fitMapToMarkers() {
        const bounds = new google.maps.LatLngBounds();

        if (this.userMarker) {
            bounds.extend(this.userMarker.getPosition());
        }

        this.nearbyMarkers.forEach(marker => {
            bounds.extend(marker.getPosition());
        });

        this.map.fitBounds(bounds);
    }

    /**
     * Draw route from user location to a destination
     */
    drawRoute(destinationLat, destinationLng) {
        const directionsService = new google.maps.DirectionsService();
        const directionsRenderer = new google.maps.DirectionsRenderer({
            map: this.map,
            polylineOptions: {
                strokeColor: '#FF0000',
                strokeWeight: 3,
                strokeOpacity: 0.7,
            },
        });

        const request = {
            origin: this.userLocation,
            destination: { lat: destinationLat, lng: destinationLng },
            travelMode: google.maps.TravelMode.DRIVING,
        };

        directionsService.route(request, (result, status) => {
            if (status === google.maps.DirectionsStatus.OK) {
                directionsRenderer.setDirections(result);
            }
        });
    }

    /**
     * Show nearby places on map
     */
    showNearbyOnMap(latitude, longitude, radius = 2000) {
        // This would typically call your backend API
        this.initMap('map-container', latitude, longitude, 15);
    }
}

// ─────────────────────────────────────────────────────
// SOS Handler
// ─────────────────────────────────────────────────────
class SheShieldSOSHandler {
    constructor() {
        this.mapHandler = new SheShieldMapHandler();
        this.sosTriggered = false;
    }

    /**
     * Get current user location using GPS
     */
    async getCurrentLocation() {
        return new Promise((resolve, reject) => {
            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(
                    (position) => {
                        const { latitude, longitude, accuracy } = position.coords;
                        resolve({ latitude, longitude, accuracy });
                    },
                    (error) => {
                        reject(new Error(`Geolocation error: ${error.message}`));
                    },
                    {
                        enableHighAccuracy: true,
                        timeout: 10000,
                        maximumAge: 0,
                    }
                );
            } else {
                reject(new Error('Geolocation not supported by this browser'));
            }
        });
    }

    /**
     * Trigger SOS with location and nearby places
     */
    async triggerSOS() {
        try {
            // Show loading state
            this.showSOSLoading();

            // Get current location
            const location = await this.getCurrentLocation();
            console.log('Current location:', location);

            // Call backend SOS endpoint
            const sosResponse = await api(
                'POST',
                '/api/v1/ai/sos-trigger',
                {
                    latitude: location.latitude,
                    longitude: location.longitude,
                    recipient_emails: [],  // Uses emergency contacts from DB
                },
                true // Requires auth
            );

            console.log('SOS Response:', sosResponse);

            // Display map with nearby places
            this.displaySOSMap(location.latitude, location.longitude, sosResponse);

            // Show confirmation
            this.showSOSConfirmation(sosResponse);

            this.sosTriggered = true;

        } catch (error) {
            console.error('SOS Error:', error);
            this.showSOSError(error.message);
        }
    }

    /**
     * Display map with SOS information
     */
    displaySOSMap(latitude, longitude, sosData) {
        // Initialize map
        this.mapHandler.initMap('sos-map-container', latitude, longitude, 15);

        // Add nearby places
        if (sosData.nearby_places) {
            const places = Object.values(sosData.nearby_places)
                .filter(p => p !== null)
                .map(place => ({
                    ...place,
                    type: place.type || 'location'
                }));

            this.mapHandler.addNearbyPlaces(places);
        }
    }

    /**
     * Show SOS confirmation UI
     */
    showSOSConfirmation(sosData) {
        const confirmationHTML = `
            <div class="sos-confirmation-popup">
                <div class="sos-popup-header">
                    <h2>🚨 SOS ACTIVATED</h2>
                    <p>Help is on the way!</p>
                </div>

                <div class="sos-popup-content">
                    <div class="location-info">
                        <h3>📍 Your Location</h3>
                        <p>Coordinates: ${sosData.location.latitude.toFixed(4)}, ${sosData.location.longitude.toFixed(4)}</p>
                        <a href="${sosData.map_links.view_link}" target="_blank" class="btn-map-link">
                            🗺️ View on Google Maps
                        </a>
                    </div>

                    <div class="nearby-places-list">
                        <h3>🏛️ Nearby Safety Places</h3>
                        ${this.formatNearbyPlaces(sosData.nearby_places)}
                    </div>

                    <div class="email-status">
                        <h3>📧 Email Alerts</h3>
                        ${this.formatEmailStatus(sosData.emails_sent)}
                    </div>

                    <div class="sos-actions">
                        <button onclick="location.reload()" class="btn btn-primary">Close</button>
                        <a href="${sosData.map_links.view_link}" target="_blank" class="btn btn-secondary">
                            Full Map View
                        </a>
                    </div>
                </div>
            </div>
        `;

        // Display in modal or dedicated container
        const container = document.getElementById('sos-confirmation-container') || 
                         document.body;
        
        const popup = document.createElement('div');
        popup.innerHTML = confirmationHTML;
        container.appendChild(popup);
    }

    /**
     * Format nearby places for display
     */
    formatNearbyPlaces(nearbyPlaces) {
        let html = '<ul class="nearby-list">';

        const icons = {
            Hospital: '🏥',
            'Police Station': '🚔',
            'Shopping Mall': '🏬',
            Restaurant: '🍽️',
        };

        for (const [key, place] of Object.entries(nearbyPlaces)) {
            if (place) {
                const icon = icons[place.type] || '📍';
                html += `
                    <li class="nearby-item">
                        <span class="icon">${icon}</span>
                        <div class="place-info">
                            <strong>${place.name}</strong><br>
                            <small>${place.distance}m away</small><br>
                            <small style="color: #999;">${place.address}</small>
                        </div>
                        <a href="https://www.google.com/maps?q=${place.lat},${place.lng}" target="_blank" class="view-btn">View</a>
                    </li>
                `;
            }
        }

        html += '</ul>';
        return html;
    }

    /**
     * Format email sending status
     */
    formatEmailStatus(emailResults) {
        let html = '<ul class="email-list">';

        emailResults.forEach(result => {
            const icon = result.success ? '✅' : '❌';
            html += `
                <li class="email-item">
                    <span>${icon}</span>
                    <strong>${result.email}</strong>
                    <span style="color: #666; font-size: 12px;">${result.message}</span>
                </li>
            `;
        });

        html += '</ul>';
        return html;
    }

    /**
     * Show loading state
     */
    showSOSLoading() {
        const loading = document.createElement('div');
        loading.className = 'sos-loading';
        loading.id = 'sos-loading-indicator';
        loading.innerHTML = `
            <div class="loading-spinner">
                <div class="spinner"></div>
                <p>Triggering SOS...</p>
                <p style="font-size: 12px; color: #999;">Getting your location and nearby places...</p>
            </div>
        `;
        document.body.appendChild(loading);
    }

    /**
     * Show error
     */
    showSOSError(errorMessage) {
        const error = document.createElement('div');
        error.className = 'sos-error-popup';
        error.innerHTML = `
            <div class="error-content">
                <h3>⚠️ Error</h3>
                <p>${errorMessage}</p>
                <button onclick="this.parentElement.parentElement.remove()">Close</button>
            </div>
        `;
        document.body.appendChild(error);

        // Remove loading indicator if present
        const loading = document.getElementById('sos-loading-indicator');
        if (loading) loading.remove();
    }
}

// ─────────────────────────────────────────────────────
// CSS Styles for SOS
// ─────────────────────────────────────────────────────
const sosStyles = `
<style>
    .sos-confirmation-popup {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0, 0, 0, 0.7);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 10000;
        padding: 20px;
    }

    .sos-popup-header {
        background: linear-gradient(135deg, #ff6b6b 0%, #ee5a6f 100%);
        color: white;
        padding: 30px;
        text-align: center;
        border-radius: 10px 10px 0 0;
    }

    .sos-popup-header h2 {
        margin: 0;
        font-size: 24px;
    }

    .sos-popup-content {
        background: white;
        border-radius: 0 0 10px 10px;
        padding: 30px;
        max-width: 500px;
        max-height: 80vh;
        overflow-y: auto;
    }

    .location-info, .nearby-places-list, .email-status {
        margin-bottom: 25px;
        padding-bottom: 20px;
        border-bottom: 1px solid #e0e0e0;
    }

    .location-info h3, .nearby-places-list h3, .email-status h3 {
        margin: 0 0 15px 0;
        color: #333;
    }

    .btn-map-link {
        display: inline-block;
        background: #007AFF;
        color: white;
        padding: 10px 15px;
        border-radius: 5px;
        text-decoration: none;
        font-weight: 500;
        margin-top: 10px;
    }

    .nearby-list, .email-list {
        list-style: none;
        padding: 0;
        margin: 0;
    }

    .nearby-item, .email-item {
        display: flex;
        align-items: flex-start;
        gap: 12px;
        padding: 12px;
        background: #f5f5f5;
        border-radius: 5px;
        margin-bottom: 10px;
    }

    .nearby-item .icon {
        font-size: 20px;
        min-width: 24px;
        text-align: center;
    }

    .place-info {
        flex: 1;
    }

    .place-info strong {
        display: block;
        margin-bottom: 5px;
    }

    .place-info small {
        display: block;
        font-size: 12px;
        color: #666;
    }

    .view-btn {
        background: white;
        color: #007AFF;
        padding: 6px 12px;
        border-radius: 3px;
        text-decoration: none;
        font-size: 12px;
        font-weight: 500;
        border: 1px solid #007AFF;
    }

    .sos-actions {
        display: flex;
        gap: 10px;
        justify-content: center;
        margin-top: 20px;
    }

    .btn {
        padding: 12px 24px;
        border-radius: 5px;
        text-decoration: none;
        border: none;
        cursor: pointer;
        font-weight: 500;
    }

    .btn-primary {
        background: #007AFF;
        color: white;
    }

    .btn-secondary {
        background: white;
        color: #007AFF;
        border: 2px solid #007AFF;
    }

    .sos-loading {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0, 0, 0, 0.7);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 9999;
    }

    .loading-spinner {
        background: white;
        padding: 40px;
        border-radius: 10px;
        text-align: center;
    }

    .spinner {
        border: 4px solid #f0f0f0;
        border-top: 4px solid #ff6b6b;
        border-radius: 50%;
        width: 40px;
        height: 40px;
        animation: spin 1s linear infinite;
        margin: 0 auto 20px;
    }

    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }

    .sos-error-popup {
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        background: white;
        border-radius: 10px;
        padding: 30px;
        box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
        z-index: 10001;
        max-width: 400px;
        text-align: center;
    }

    .error-content h3 {
        color: #d32f2f;
        margin-top: 0;
    }

    #sos-map-container {
        width: 100%;
        height: 400px;
        border-radius: 5px;
        margin: 20px 0;
    }
</style>
`;

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    // Inject styles if not already present
    if (!document.querySelector('style[data-sos-styles]')) {
        const styleEl = document.createElement('style');
        styleEl.setAttribute('data-sos-styles', 'true');
        styleEl.innerHTML = sosStyles.replace(/<\/?style>/g, '');
        document.head.appendChild(styleEl);
    }
});

// Export for use in app
window.SheShieldMapHandler = SheShieldMapHandler;
window.SheShieldSOSHandler = SheShieldSOSHandler;
