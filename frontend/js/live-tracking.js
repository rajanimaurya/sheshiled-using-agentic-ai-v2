/* ═══════════════════════════════════════════════════════════════════════════
   SHESHIELD - LIVE LOCATION TRACKING MODULE
   
   Features:
   ✓ Continuous GPS tracking (every 5-10 seconds)
   ✓ Real-time location updates
   ✓ Live nearby places display
   ✓ Live route visualization
   ✓ Family dashboard link
   ✓ Movement tracking
   ═══════════════════════════════════════════════════════════════════════════ */

// ────────────────────────────────────────────────────────────────────────────
// LIVE TRACKING STATE
// ────────────────────────────────────────────────────────────────────────────

const liveTrackingState = {
  isActive: false,
  sessionId: null,
  watchId: null,
  updateInterval: 5000,  // Update every 5 seconds
  locationsTracked: [],
  currentLocation: null,
  nearbyPlaces: {},
  nearestSafePlace: null,
  route: null,
};

// ────────────────────────────────────────────────────────────────────────────
// START LIVE TRACKING (When SOS clicked)
// ────────────────────────────────────────────────────────────────────────────

async function startLiveTracking(latitude, longitude) {
  console.log(`🚨 Starting LIVE TRACKING from ${latitude}, ${longitude}`);
  
  try {
    // Call backend to start session
    const response = await api(
      'POST',
      '/api/v1/live/start',
      {
        latitude: latitude,
        longitude: longitude,
        radius: 2000
      },
      true  // auth needed
    );
    
    console.log('✅ Live tracking session started:', response);
    
    liveTrackingState.isActive = true;
    liveTrackingState.sessionId = response.user_id;
    liveTrackingState.currentLocation = response.current_location;
    liveTrackingState.nearestSafePlace = response.nearest_safe_place;
    
    // Show live tracking UI
    showLiveTrackingUI();
    
    // Start continuous GPS updates
    startContinuousGPS();
    
    // Show family dashboard link
    showFamilyDashboardLink();
    
  } catch (error) {
    console.error('❌ Failed to start live tracking:', error);
    showAlert(`❌ Live tracking failed: ${error.message}`, 'error');
  }
}

// ────────────────────────────────────────────────────────────────────────────
// CONTINUOUS GPS TRACKING (Every 5-10 seconds)
// ────────────────────────────────────────────────────────────────────────────

function startContinuousGPS() {
  console.log('📍 Starting continuous GPS tracking...');
  
  if (!navigator.geolocation) {
    showAlert('❌ Geolocation not supported', 'error');
    return;
  }
  
  // Watch position - continuous updates
  liveTrackingState.watchId = navigator.geolocation.watchPosition(
    async (position) => {
      const { latitude, longitude } = position.coords;
      
      console.log(`📍 New location: ${latitude}, ${longitude}`);
      
      // Update UI immediately
      updateLiveLocationUI(latitude, longitude);
      
      // Send to backend (debounced, every 5 seconds)
      await updateBackendLocation(latitude, longitude);
    },
    
    (error) => {
      console.error('❌ GPS Error:', error);
      showLiveTrackingAlert(`⚠️ GPS Error: ${error.message}`, 'warning');
    },
    
    {
      enableHighAccuracy: true,  // Best accuracy
      timeout: 10000,            // 10s timeout
      maximumAge: 0              // Always fresh
    }
  );
}

// ────────────────────────────────────────────────────────────────────────────
// UPDATE BACKEND WITH NEW LOCATION
// ────────────────────────────────────────────────────────────────────────────

let lastUpdateTime = 0;

async function updateBackendLocation(latitude, longitude) {
  const now = Date.now();
  
  // Only update backend every 5 seconds (debounce)
  if (now - lastUpdateTime < 5000) {
    return;
  }
  lastUpdateTime = now;
  
  try {
    const response = await api(
      'POST',
      '/api/v1/live/update',
      {
        latitude: latitude,
        longitude: longitude,
        radius: 2000
      },
      true  // auth needed
    );
    
    // Update live tracking state
    liveTrackingState.currentLocation = response.current_location;
    liveTrackingState.nearbyPlaces = response.all_nearby_places;
    liveTrackingState.nearestSafePlace = response.nearest_safe_place;
    liveTrackingState.locationsTracked.push({
      latitude,
      longitude,
      timestamp: response.timestamp
    });
    
    console.log(`✅ Backend updated | Distance to nearest place: ${response.nearest_safe_place?.total_distance_m || 'N/A'}m`);
    
    // Update live UI
    updateLiveMapDisplay();
    updateNearbyPlacesLive(response.all_nearby_places);
    updateNearestPlaceDisplay(response.nearest_safe_place);
    
  } catch (error) {
    console.error('⚠️ Backend update failed:', error);
    // Continue tracking even if update fails
  }
}

// ────────────────────────────────────────────────────────────────────────────
// LIVE TRACKING UI - LOCATION DISPLAY
// ────────────────────────────────────────────────────────────────────────────

function updateLiveLocationUI(latitude, longitude) {
  const el = document.getElementById('live-location-display');
  if (!el) return;
  
  el.innerHTML = `
    <div class="live-location-badge">
      📍 <span class="blinking">●</span> LIVE TRACKING ACTIVE
    </div>
    <div class="live-coordinates">
      Lat: <code>${latitude.toFixed(6)}</code>
      Lon: <code>${longitude.toFixed(6)}</code>
    </div>
    <div class="live-map-link">
      <a href="https://maps.google.com?q=${latitude},${longitude}" target="_blank" class="btn-primary">
        🗺️ View on Maps
      </a>
    </div>
  `;
}

// ────────────────────────────────────────────────────────────────────────────
// LIVE MAP DISPLAY (Like Google Maps)
// ────────────────────────────────────────────────────────────────────────────

function updateLiveMapDisplay() {
  const el = document.getElementById('live-map-container');
  if (!el) return;
  
  const { currentLocation, nearestSafePlace } = liveTrackingState;
  
  if (!currentLocation) return;
  
  const mapHTML = `
    <div class="live-map-wrapper">
      <div class="map-header">
        📍 LIVE LOCATION MAP
        <span class="tracking-timer">${getTrackingDuration()}</span>
      </div>
      
      <div class="map-content">
        <!-- Embedded Google Map -->
        <iframe 
          width="100%" 
          height="400" 
          frameborder="0" 
          style="border:0; border-radius: 8px;"
          src="https://www.google.com/maps/embed?pb=!1m14!1m8!1m3!1d3600!2d${currentLocation.longitude}!3d${currentLocation.latitude}!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x0%3A0x0!2zM!5e0!3m2!1sen!2sin!4v1234567890"
          allowfullscreen="" 
          loading="lazy">
        </iframe>
      </div>
      
      <div class="map-info">
        <div class="current-location-badge">
          🔴 Current Location: 
          (${currentLocation.latitude.toFixed(6)}, ${currentLocation.longitude.toFixed(6)})
        </div>
        
        ${nearestSafePlace ? `
          <div class="route-badge">
            🚗 Nearest Safe Place: <strong>${nearestSafePlace.name}</strong>
            📏 ${nearestSafePlace.distance_m}m away
            <a href="${nearestSafePlace.maps_link}" target="_blank" class="btn-secondary">
              Get Directions
            </a>
          </div>
        ` : ''}
      </div>
    </div>
  `;
  
  el.innerHTML = mapHTML;
}

// ────────────────────────────────────────────────────────────────────────────
// LIVE NEARBY PLACES (Real-time distances!)
// ────────────────────────────────────────────────────────────────────────────

function updateNearbyPlacesLive(nearbyPlaces) {
  const el = document.getElementById('live-nearby-places');
  if (!el) return;
  
  let placesHTML = '<div class="nearby-places-live">';
  
  const typeOrder = ['police', 'hospital', 'mall', 'restaurant'];
  const iconMap = {
    police: '🚔',
    hospital: '🏥',
    mall: '🏬',
    restaurant: '🍽️'
  };
  
  typeOrder.forEach(type => {
    const place = nearbyPlaces[type];
    if (place) {
      const icon = iconMap[type] || '📍';
      const distKm = (place.distance_m / 1000).toFixed(2);
      
      placesHTML += `
        <div class="nearby-place-live-card">
          <div class="place-icon">${icon}</div>
          <div class="place-info">
            <strong>${place.name}</strong><br>
            <span class="distance-live">
              📏 ${place.distance_m}m (${distKm}km) away
            </span><br>
            <small>${place.address}</small>
          </div>
          <div class="place-action">
            <a href="https://www.google.com/maps/dir/?api=1&origin=${liveTrackingState.currentLocation.latitude},${liveTrackingState.currentLocation.longitude}&destination=${place.lat},${place.lng}&travelmode=driving" 
               target="_blank" 
               class="btn-get-directions">
              🗺️ Route
            </a>
          </div>
        </div>
      `;
    }
  });
  
  placesHTML += '</div>';
  el.innerHTML = placesHTML;
}

// ────────────────────────────────────────────────────────────────────────────
// NEAREST SAFE PLACE (Highlighted)
// ────────────────────────────────────────────────────────────────────────────

function updateNearestPlaceDisplay(nearestPlace) {
  const el = document.getElementById('nearest-safe-place-live');
  if (!el || !nearestPlace) return;
  
  el.innerHTML = `
    <div class="nearest-place-card">
      <div class="badge-closest">🎯 CLOSEST SAFE PLACE</div>
      <h3>${nearestPlace.name}</h3>
      <p class="distance-highlight">
        📏 ${nearestPlace.distance_m} meters away
      </p>
      <p>${nearestPlace.type}</p>
      <a href="${nearestPlace.maps_link}" target="_blank" class="btn-primary btn-lg">
        🚗 GET DIRECTIONS →
      </a>
    </div>
  `;
}

// ────────────────────────────────────────────────────────────────────────────
// SHOW LIVE TRACKING UI
// ────────────────────────────────────────────────────────────────────────────

function showLiveTrackingUI() {
  // Hide SOS popup
  hideSOSPopup();
  
  // Hide main screens
  document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
  
  // Create live tracking screen
  const liveScreen = document.createElement('div');
  liveScreen.id = 'screen-live-tracking';
  liveScreen.className = 'screen active';
  liveScreen.innerHTML = `
    <div class="live-tracking-container">
      <!-- Header -->
      <div class="live-header">
        <div class="live-status">
          <span class="live-indicator">🔴 LIVE</span>
          <span class="tracking-timer">00:00</span>
        </div>
        <div class="tracking-stats">
          <span>📍 Locations: <strong id="location-count">1</strong></span>
          <span>🚗 Distance: <strong id="distance-traveled">0</strong>m</span>
        </div>
        <button onclick="endLiveTracking()" class="btn-end-tracking">
          ⏹️ END TRACKING
        </button>
      </div>
      
      <!-- Current Location -->
      <div id="live-location-display"></div>
      
      <!-- Live Map -->
      <div id="live-map-container"></div>
      
      <!-- Nearest Safe Place -->
      <div id="nearest-safe-place-live"></div>
      
      <!-- All Nearby Places -->
      <h3>All Nearby Safe Places (LIVE)</h3>
      <div id="live-nearby-places"></div>
      
      <!-- Family Dashboard Link -->
      <div id="family-dashboard-link"></div>
    </div>
  `;
  
  document.body.appendChild(liveScreen);
}

// ────────────────────────────────────────────────────────────────────────────
// FAMILY DASHBOARD LINK (Share with contacts)
// ────────────────────────────────────────────────────────────────────────────

function showFamilyDashboardLink() {
  const el = document.getElementById('family-dashboard-link');
  if (!el) return;
  
  const dashboardLink = `${window.location.origin}?view=family-dashboard&user=${liveTrackingState.sessionId}`;
  
  el.innerHTML = `
    <div class="family-dashboard-info">
      <h4>📱 Share with Family</h4>
      <p>Your family can see live location here:</p>
      <div class="dashboard-link-box">
        <code>${dashboardLink}</code>
        <button onclick="copyToClipboard('${dashboardLink}')" class="btn-copy">
          📋 Copy Link
        </button>
      </div>
      <p class="info-text">
        Family members can open this link to see:
        ✅ Your live location on map
        ✅ Nearby safe places with distances
        ✅ Route to nearest safety
        ✅ Your movement history
      </p>
    </div>
  `;
}

// ────────────────────────────────────────────────────────────────────────────
// END LIVE TRACKING
// ────────────────────────────────────────────────────────────────────────────

async function endLiveTracking() {
  if (!confirm('End live tracking?')) return;
  
  console.log('🛑 Ending live tracking...');
  
  try {
    // Stop GPS tracking
    if (liveTrackingState.watchId) {
      navigator.geolocation.clearWatch(liveTrackingState.watchId);
    }
    
    // Call backend to end session
    const response = await api('POST', '/api/v1/live/end', {}, true);
    
    console.log('✅ Tracking ended:', response);
    
    // Show summary
    showAlert(`
      ✅ Tracking Ended!
      📍 Locations tracked: ${response.summary.locations_tracked}
      🚗 Distance traveled: ${response.summary.total_distance_m}m
      ⏱️ Duration: ${response.summary.duration_minutes} minutes
    `, 'success');
    
    // Reset state
    liveTrackingState.isActive = false;
    liveTrackingState.watchId = null;
    
    // Go back to home
    setTimeout(() => goTo('home'), 2000);
    
  } catch (error) {
    console.error('❌ Failed to end tracking:', error);
    showAlert(`Error ending tracking: ${error.message}`, 'error');
  }
}

// ────────────────────────────────────────────────────────────────────────────
// HELPER FUNCTIONS
// ────────────────────────────────────────────────────────────────────────────

function getTrackingDuration() {
  // Return formatted duration
  return new Date().toLocaleTimeString();
}

function showLiveTrackingAlert(msg, type = 'info') {
  // Show alert in live tracking UI
  const el = document.createElement('div');
  el.className = `live-tracking-alert alert-${type}`;
  el.textContent = msg;
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 3000);
}

function copyToClipboard(text) {
  navigator.clipboard.writeText(text);
  showAlert('✅ Link copied!', 'success');
}
