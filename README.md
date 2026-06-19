# SmartRoute

Optimizador de ruta de despacho. Permite ingresar varias direcciones de entrega y generar la ruta óptima según dos criterios:

- **Por distancia** — usa OSRM `/trip` endpoint (TSP solver) para reordenar los waypoints.
- **Por sector** — agrupa las direcciones por comuna/barrio (vía Nominatim geocoding) y luego optimiza dentro de cada grupo.

## Características

- Tres formas de añadir direcciones: manual con autocomplete (Nominatim), carga masiva (CSV o lista), o click en el mapa.
- Origen tomado desde la geolocalización del navegador ("Mi ubicación").
- Mapa embebido con Leaflet + OpenStreetMap, ruta dibujada y panel con orden de paradas, distancia y duración total.
- Botón **"Abrir en Google Maps"** que arma el deep-link con todos los waypoints (enlace externo, no requiere API key).
- Persistencia en SQLite: direcciones frecuentes e historial de rutas.
- **No requiere API keys** — usa servicios gratuitos: Nominatim, OSRM, OpenStreetMap tiles.

## Stack

- **Backend**: FastAPI + SQLModel + httpx
- **Frontend**: HTML + Vanilla JS + Leaflet.js + OpenStreetMap
- **Geocoding**: Nominatim (OpenStreetMap)
- **Routing**: OSRM (Open Source Routing Machine)
- **DB**: SQLite

## Setup

```bash
python -m venv .venv
source .venv/bin/activate           # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env

uvicorn app.main:app --reload
```

Luego abre http://localhost:8000

## Tests

```bash
pytest
```

## Estructura

```
app/
  main.py          FastAPI app
  config.py        Carga de variables de entorno
  database.py      Engine SQLite y init_db
  models.py        SQLModel: Address, Route, RouteStop
  schemas.py       Pydantic request/response
  services/
    google_client.py  Shared httpx client (Nominatim/OSRM)
    geocoding.py      Wrapper Nominatim geocoding
    optimizer.py      optimize_by_distance / optimize_by_sector (OSRM)
  routers/
    addresses.py
    routes.py
static/
  index.html
  css/styles.css
  js/app.js, map.js, input.js
tests/
```
