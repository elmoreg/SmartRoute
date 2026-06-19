// Main app state and event wiring.

const State = {
  origin: null, // { lat, lng }
  addresses: [], // [{ id, formatted_address, lat, lng, sector, ... }]
  lastResult: null,
};

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`API ${path} failed: ${response.status} ${detail}`);
  }
  return response.json();
}

function renderAddresses() {
  const list = document.getElementById('address-list');
  list.innerHTML = '';
  State.addresses.forEach((addr, idx) => {
    const li = document.createElement('li');
    li.innerHTML = `
      <div class="info">
        <div><strong>${idx + 1}.</strong> ${addr.formatted_address}</div>
        ${addr.sector ? `<span class="sector">${addr.sector}</span>` : ''}
      </div>
      <button class="remove" data-idx="${idx}" title="Quitar">&times;</button>
    `;
    list.appendChild(li);
  });
  list.querySelectorAll('.remove').forEach((btn) => {
    btn.addEventListener('click', () => {
      const i = Number(btn.dataset.idx);
      State.addresses.splice(i, 1);
      renderAddresses();
      SmartMap.refreshAddressMarkers(State.addresses);
    });
  });
  SmartMap.refreshAddressMarkers(State.addresses);
}

function setOrigin(lat, lng, label) {
  State.origin = { lat, lng };
  document.getElementById('origin-text').textContent = label || `${lat.toFixed(5)}, ${lng.toFixed(5)}`;
  SmartMap.setOrigin(lat, lng, label);
}

async function addAddressFromText(text) {
  if (!text || !text.trim()) return;
  try {
    const addr = await api('/api/addresses/geocode', {
      method: 'POST',
      body: JSON.stringify({ text }),
    });
    if (!State.addresses.find((a) => a.id === addr.id)) {
      State.addresses.push(addr);
      renderAddresses();
    }
  } catch (err) {
    alert(`No se pudo geocodificar "${text}": ${err.message}`);
  }
}

async function addBulkAddresses(text) {
  const texts = SmartInput.parseBulk(text);
  if (!texts.length) return;
  try {
    const results = await api('/api/addresses/bulk', {
      method: 'POST',
      body: JSON.stringify({ texts }),
    });
    results.forEach((addr) => {
      if (!State.addresses.find((a) => a.id === addr.id)) {
        State.addresses.push(addr);
      }
    });
    renderAddresses();
  } catch (err) {
    alert(`Error en carga masiva: ${err.message}`);
  }
}

function buildGoogleMapsUrl(origin, addresses) {
  if (!addresses.length) return '#';
  const base = 'https://www.google.com/maps/dir/?api=1';
  const originParam = `${origin.lat},${origin.lng}`;
  const destination = addresses[addresses.length - 1];
  const waypoints = addresses.slice(0, -1).map((a) => `${a.lat},${a.lng}`).join('|');
  const params = new URLSearchParams({
    origin: originParam,
    destination: `${destination.lat},${destination.lng}`,
    travelmode: 'driving',
  });
  if (waypoints) params.set('waypoints', waypoints);
  return `${base}&${params.toString()}`;
}

function formatDuration(seconds) {
  const h = Math.floor(seconds / 3600);
  const m = Math.round((seconds % 3600) / 60);
  return h ? `${h} h ${m} min` : `${m} min`;
}

function renderResult(route) {
  document.getElementById('result-section').hidden = false;
  document.getElementById('result-summary').textContent =
    `${route.stops.length} paradas — ${(route.total_distance_m / 1000).toFixed(1)} km · ${formatDuration(route.total_duration_s)}`;

  const ol = document.getElementById('result-stops');
  ol.innerHTML = '';
  route.stops.forEach((stop) => {
    const li = document.createElement('li');
    li.innerHTML = `
      <div>${stop.address.formatted_address}</div>
      ${stop.address.sector ? `<span class="sector">${stop.address.sector}</span>` : ''}
      <div class="leg">${(stop.leg_distance_m / 1000).toFixed(1)} km · ${formatDuration(stop.leg_duration_s)}</div>
    `;
    ol.appendChild(li);
  });

  const orderedAddresses = route.stops.map((s) => s.address);
  SmartMap.drawRoute({ lat: route.origin_lat, lng: route.origin_lng }, orderedAddresses, route.overview_polyline);

  const link = document.getElementById('open-in-gmaps');
  link.href = buildGoogleMapsUrl({ lat: route.origin_lat, lng: route.origin_lng }, orderedAddresses);
}

async function optimize() {
  if (!State.origin) {
    alert('Define el origen primero (botón "Usar mi ubicación").');
    return;
  }
  if (!State.addresses.length) {
    alert('Añade al menos una dirección.');
    return;
  }
  const mode = document.querySelector('input[name="mode"]:checked').value;
  try {
    const route = await api('/api/routes/optimize', {
      method: 'POST',
      body: JSON.stringify({
        origin: State.origin,
        address_ids: State.addresses.map((a) => a.id),
        mode,
      }),
    });
    State.lastResult = route;
    renderResult(route);
    refreshHistory();
  } catch (err) {
    alert(`Error optimizando: ${err.message}`);
  }
}

async function refreshHistory() {
  try {
    const routes = await api('/api/routes');
    const ul = document.getElementById('history-list');
    ul.innerHTML = '';
    routes.slice(0, 10).forEach((r) => {
      const li = document.createElement('li');
      const date = new Date(r.created_at).toLocaleString();
      li.textContent = `${date} · ${r.mode} · ${r.stops.length} paradas · ${(r.total_distance_m / 1000).toFixed(1)} km`;
      li.style.cursor = 'pointer';
      li.addEventListener('click', () => renderResult(r));
      ul.appendChild(li);
    });
  } catch (err) {
    console.error(err);
  }
}

function bindEvents() {
  document.getElementById('btn-locate').addEventListener('click', () => {
    if (!navigator.geolocation) {
      alert('Tu navegador no soporta geolocalización.');
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => setOrigin(pos.coords.latitude, pos.coords.longitude, 'Mi ubicación'),
      (err) => alert(`No se pudo obtener tu ubicación: ${err.message}`)
    );
  });

  const input = document.getElementById('address-input');
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      addAddressFromText(input.value);
      input.value = '';
    }
  });

  // Listen for autocomplete selection from Nominatim (fired by map.js)
  document.addEventListener('smartmap:autocomplete', (e) => {
    addAddressFromText(e.detail);
    input.value = '';
  });

  document.getElementById('btn-bulk').addEventListener('click', () => {
    const ta = document.getElementById('bulk-input');
    addBulkAddresses(ta.value);
    ta.value = '';
  });

  document.getElementById('btn-optimize').addEventListener('click', optimize);
  document.getElementById('btn-refresh-history').addEventListener('click', refreshHistory);

  SmartMap.onMapClick = (lat, lng) => {
    addAddressFromText(`${lat},${lng}`);
  };
}

document.addEventListener('smartmap:ready', () => {
  bindEvents();
  refreshHistory();
});
