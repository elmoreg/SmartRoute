// Google Maps integration: map init, autocomplete, drawing routes.

const SmartMap = {
  map: null,
  directionsService: null,
  directionsRenderer: null,
  originMarker: null,
  addressMarkers: [],
  autocomplete: null,
  onMapClick: null, // set by app.js

  init() {
    this.map = new google.maps.Map(document.getElementById('map'), {
      center: { lat: -33.4489, lng: -70.6693 }, // Santiago by default
      zoom: 12,
      mapTypeControl: false,
      streetViewControl: false,
    });

    this.directionsService = new google.maps.DirectionsService();
    this.directionsRenderer = new google.maps.DirectionsRenderer({
      map: this.map,
      suppressMarkers: false,
      preserveViewport: false,
    });

    this.map.addListener('click', (event) => {
      if (this.onMapClick) {
        this.onMapClick(event.latLng.lat(), event.latLng.lng());
      }
    });

    const input = document.getElementById('address-input');
    if (input && google.maps.places) {
      this.autocomplete = new google.maps.places.Autocomplete(input, {
        fields: ['formatted_address', 'geometry', 'place_id'],
      });
    }
  },

  setOrigin(lat, lng, label) {
    if (this.originMarker) this.originMarker.setMap(null);
    this.originMarker = new google.maps.Marker({
      position: { lat, lng },
      map: this.map,
      label: 'O',
      title: label || 'Origen',
    });
    this.map.panTo({ lat, lng });
  },

  addAddressMarker(lat, lng, label) {
    const marker = new google.maps.Marker({
      position: { lat, lng },
      map: this.map,
      label: String(this.addressMarkers.length + 1),
      title: label,
    });
    this.addressMarkers.push(marker);
    return marker;
  },

  clearAddressMarkers() {
    this.addressMarkers.forEach((m) => m.setMap(null));
    this.addressMarkers = [];
  },

  refreshAddressMarkers(addresses) {
    this.clearAddressMarkers();
    addresses.forEach((a) => this.addAddressMarker(a.lat, a.lng, a.formatted_address));
  },

  drawRoute(originLatLng, orderedAddresses) {
    if (!orderedAddresses.length) return;
    const waypoints = orderedAddresses.slice(0, -1).map((a) => ({
      location: { lat: a.lat, lng: a.lng },
      stopover: true,
    }));
    const destination = orderedAddresses[orderedAddresses.length - 1];

    this.directionsService.route(
      {
        origin: originLatLng,
        destination: { lat: destination.lat, lng: destination.lng },
        waypoints,
        optimizeWaypoints: false, // already optimized server-side
        travelMode: google.maps.TravelMode.DRIVING,
      },
      (result, status) => {
        if (status === 'OK') {
          this.directionsRenderer.setDirections(result);
          this.clearAddressMarkers();
        } else {
          console.error('Directions request failed:', status);
        }
      }
    );
  },

  clearRoute() {
    this.directionsRenderer.setDirections({ routes: [] });
  },
};

// Called by Google Maps script via &callback=initMap
function initMap() {
  SmartMap.init();
  document.dispatchEvent(new CustomEvent('smartmap:ready'));
}

window.SmartMap = SmartMap;
