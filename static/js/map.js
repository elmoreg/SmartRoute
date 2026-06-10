// Leaflet + OpenStreetMap integration: map init, markers, polyline drawing, autocomplete.

/**
 * Decode a Google-encoded polyline string (used by OSRM too) into an array of
 * [lat, lng] pairs suitable for L.polyline.
 */
function decodePolyline(encoded) {
  const points = [];
  let index = 0;
  let lat = 0;
  let lng = 0;

  while (index < encoded.length) {
    let b;
    let shift = 0;
    let result = 0;
    do {
      b = encoded.charCodeAt(index++) - 63;
      result |= (b & 0x1f) << shift;
      shift += 5;
    } while (b >= 0x20);
    lat += (result & 1) ? ~(result >> 1) : (result >> 1);

    shift = 0;
    result = 0;
    do {
      b = encoded.charCodeAt(index++) - 63;
      result |= (b & 0x1f) << shift;
      shift += 5;
    } while (b >= 0x20);
    lng += (result & 1) ? ~(result >> 1) : (result >> 1);

    points.push([lat / 1e5, lng / 1e5]);
  }
  return points;
}

const SmartMap = {
  map: null,
  originMarker: null,
  addressMarkers: [],
  routePolyline: null,
  routeMarkers: [],
  onMapClick: null, // set by app.js
  _autocompleteTimer: null,

  init() {
    this.map = L.map('map', {
      center: [-33.4489, -70.6693], // Santiago by default
      zoom: 12,
      zoomControl: true,
    });

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      maxZoom: 19,
    }).addTo(this.map);

    this.map.on('click', (e) => {
      if (this.onMapClick) {
        this.onMapClick(e.latlng.lat, e.latlng.lng);
      }
    });

    // Set up Nominatim autocomplete on the address input
    this._initAutocomplete();
  },

  _initAutocomplete() {
    const input = document.getElementById('address-input');
    const list = document.getElementById('autocomplete-list');
    if (!input || !list) return;

    input.addEventListener('input', () => {
      clearTimeout(this._autocompleteTimer);
      const query = input.value.trim();
      if (query.length < 3) {
        list.innerHTML = '';
        list.style.display = 'none';
        return;
      }
      // Debounce 400ms to respect Nominatim usage policy
      this._autocompleteTimer = setTimeout(async () => {
        try {
          const url = `https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(query)}&format=json&addressdetails=1&limit=5`;
          const resp = await fetch(url, {
            headers: { 'User-Agent': 'SmartRoute/1.0' },
          });
          const results = await resp.json();
          list.innerHTML = '';
          if (!results.length) {
            list.style.display = 'none';
            return;
          }
          results.forEach((r) => {
            const li = document.createElement('li');
            li.textContent = r.display_name;
            li.addEventListener('click', () => {
              input.value = r.display_name;
              list.innerHTML = '';
              list.style.display = 'none';
              // Dispatch a custom event so app.js can pick it up
              document.dispatchEvent(new CustomEvent('smartmap:autocomplete', { detail: r.display_name }));
            });
            list.appendChild(li);
          });
          list.style.display = 'block';
        } catch (err) {
          console.error('Autocomplete error:', err);
        }
      }, 400);
    });

    // Hide list when clicking outside
    document.addEventListener('click', (e) => {
      if (!input.contains(e.target) && !list.contains(e.target)) {
        list.innerHTML = '';
        list.style.display = 'none';
      }
    });
  },

  setOrigin(lat, lng, label) {
    if (this.originMarker) {
      this.map.removeLayer(this.originMarker);
    }
    this.originMarker = L.marker([lat, lng], {
      title: label || 'Origen',
    }).addTo(this.map);
    this.originMarker.bindTooltip('O', { permanent: true, direction: 'center', className: 'marker-label' });
    this.map.panTo([lat, lng]);
  },

  addAddressMarker(lat, lng, label) {
    const marker = L.marker([lat, lng], {
      title: label,
    }).addTo(this.map);
    marker.bindTooltip(String(this.addressMarkers.length + 1), {
      permanent: true,
      direction: 'center',
      className: 'marker-label',
    });
    this.addressMarkers.push(marker);
    return marker;
  },

  clearAddressMarkers() {
    this.addressMarkers.forEach((m) => this.map.removeLayer(m));
    this.addressMarkers = [];
  },

  refreshAddressMarkers(addresses) {
    this.clearAddressMarkers();
    addresses.forEach((a) => this.addAddressMarker(a.lat, a.lng, a.formatted_address));
  },

  drawRoute(originLatLng, orderedAddresses, overviewPolyline) {
    this.clearRoute();
    this.clearAddressMarkers();

    if (!orderedAddresses.length) return;

    // Draw polyline from encoded string if available
    if (overviewPolyline) {
      const latlngs = decodePolyline(overviewPolyline);
      this.routePolyline = L.polyline(latlngs, {
        color: '#2563eb',
        weight: 5,
        opacity: 0.7,
      }).addTo(this.map);
      this.map.fitBounds(this.routePolyline.getBounds(), { padding: [30, 30] });
    }

    // Add origin marker
    const originM = L.marker([originLatLng.lat, originLatLng.lng]).addTo(this.map);
    originM.bindTooltip('O', { permanent: true, direction: 'center', className: 'marker-label' });
    this.routeMarkers.push(originM);

    // Add numbered stop markers
    orderedAddresses.forEach((a, i) => {
      const m = L.marker([a.lat, a.lng]).addTo(this.map);
      m.bindTooltip(String(i + 1), { permanent: true, direction: 'center', className: 'marker-label' });
      this.routeMarkers.push(m);
    });

    // Fit bounds if no polyline was available
    if (!overviewPolyline) {
      const allPoints = [[originLatLng.lat, originLatLng.lng], ...orderedAddresses.map((a) => [a.lat, a.lng])];
      this.map.fitBounds(allPoints, { padding: [30, 30] });
    }
  },

  clearRoute() {
    if (this.routePolyline) {
      this.map.removeLayer(this.routePolyline);
      this.routePolyline = null;
    }
    this.routeMarkers.forEach((m) => this.map.removeLayer(m));
    this.routeMarkers = [];
  },
};

// Initialize the map immediately (no callback needed unlike Google Maps)
document.addEventListener('DOMContentLoaded', () => {
  SmartMap.init();
  document.dispatchEvent(new CustomEvent('smartmap:ready'));
});

window.SmartMap = SmartMap;
