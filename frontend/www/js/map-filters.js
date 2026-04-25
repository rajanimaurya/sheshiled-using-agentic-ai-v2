/* ═══════════════════════════════════════════════════════════════════════════
   SHESHIELD — map-filters.js
   Handles: Location search bar on the Map screen.

   Filter chip logic (Hospital / Restaurant / Mall / Police) lives in app.js
   because it needs the global `map`, `currentLocation`, etc.

   This file:
     ✓ searchLocation() — text search using Google Maps Geocoder (client-side)
       → Updates global `currentLocation`
       → Updates `userMarker` on the map
       → Calls `loadNearbyPlaces()` to refresh nearby markers
   ═══════════════════════════════════════════════════════════════════════════ */

/**
 * Search a location by name and pan the map to it.
 * Uses Google Maps Geocoder (client-side) — more accurate than Nominatim for Indian addresses.
 * Also updates `currentLocation` so filter buttons work correctly after search.
 */
async function searchLocation() {
  const input = document.getElementById('map-search-input');
  if (!input) return;

  const query = input.value.trim();
  if (!query) {
    if (typeof toast === 'function') toast('type location', 'error');
    return;
  }

  if (typeof toast === 'function') toast('find it ...', 'info');

  // ── Google Maps Geocoder (preferred — client-side, accurate, India-specific) ──
  if (window.google && google.maps && google.maps.Geocoder) {
    const geocoder = new google.maps.Geocoder();
    geocoder.geocode(
      {
        address: query,
        region: 'IN',
        componentRestrictions: { country: 'IN' },
      },
      (results, status) => {
        if (status === 'OK' && results && results.length > 0) {
          const loc = results[0].geometry.location;

          // ✅ Update global currentLocation — this is the key fix
          window.currentLocation = { lat: loc.lat(), lng: loc.lng() };

          // Pan + zoom map
          if (window.map) {
            window.map.panTo(window.currentLocation);
            window.map.setZoom(16);
          }

          // Update user marker
          if (window.userMarker) window.userMarker.setMap(null);
          if (window.map && window.google) {
            window.userMarker = new google.maps.Marker({
              position: window.currentLocation,
              map: window.map,
              title: query,
              icon: {
                path: google.maps.SymbolPath.CIRCLE,
                scale: 10,
                fillColor: '#c8102e',
                fillOpacity: 1,
                strokeColor: 'white',
                strokeWeight: 3,
              },
              zIndex: 999,
            });
          }

          // Load nearby places at the new location
          if (typeof loadNearbyPlaces === 'function') {
            loadNearbyPlaces(window.currentLocation);
          }

          if (typeof toast === 'function') {
            toast('✅ ' + results[0].formatted_address, 'success');
          }
        } else {
          if (typeof toast === 'function') {
            toast('Location nahi mili. Aur detail mein likho (jaise: Hazratganj, Lucknow)', 'error');
          }
        }
      }
    );
    return;
  }

  // ── Fallback: Backend Nominatim geocode (if Google Maps not ready) ──
  try {
    const data = await api('POST', '/api/v1/ai/geocode', { query }, false);

    if (data && data.found && data.lat && data.lng) {
      window.currentLocation = { lat: data.lat, lng: data.lng };

      if (window.map) {
        window.map.panTo(window.currentLocation);
        window.map.setZoom(16);
      }

      if (window.userMarker) window.userMarker.setMap(null);
      if (window.map && window.google) {
        window.userMarker = new google.maps.Marker({
          position: window.currentLocation,
          map: window.map,
          title: query,
          icon: {
            path: google.maps.SymbolPath.CIRCLE,
            scale: 10,
            fillColor: '#c8102e',
            fillOpacity: 1,
            strokeColor: 'white',
            strokeWeight: 3,
          },
          zIndex: 999,
        });
      }

      if (typeof loadNearbyPlaces === 'function') {
        loadNearbyPlaces(window.currentLocation);
      }

      if (typeof toast === 'function') toast('✅ Mila: ' + query, 'success');
    } else {
      if (typeof toast === 'function') {
        toast('Location nahi mili: ' + query + '. Aur detail mein likho.', 'error');
      }
    }
  } catch (e) {
    console.error('searchLocation fallback error:', e);
    if (typeof toast === 'function') toast('Search mein error aaya, dobara try karo', 'error');
  }
}
