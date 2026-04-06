# SmartRoute

Optimizador de ruta de despacho. Permite ingresar varias direcciones de entrega y generar la ruta óptima en Google Maps según dos criterios:

- **Por distancia** — usa Google Directions API con `optimize:true` para reordenar los waypoints.
- **Por sector** — agrupa las direcciones por comuna/barrio (vía Google Geocoding) y luego optimiza dentro de cada grupo.

## Características

- Tres formas de añadir direcciones: manual con autocomplete, carga masiva (CSV o lista), o click en el mapa.
- Origen tomado desde la geolocalización del navegador ("Mi ubicación").
- Mapa embebido con la ruta dibujada y panel con orden de paradas, distancia y duración total.
- Botón **"Abrir en Google Maps"** que arma el deep-link con todos los waypoints.
- Persistencia en SQLite: direcciones frecuentes e historial de rutas.

## Stack

- **Backend**: FastAPI + SQLModel + httpx
- **Frontend**: HTML + Vanilla JS + Google Maps JavaScript API
- **DB**: SQLite

## Setup

```bash
python -m venv .venv
source .venv/bin/activate           # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# Editar .env y poner tu GOOGLE_MAPS_API_KEY

uvicorn app.main:app --reload
```

Luego abre http://localhost:8000

### APIs de Google necesarias

Habilita en tu proyecto de Google Cloud:

- Maps JavaScript API
- Places API
- Geocoding API
- Directions API

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
    google_client.py
    geocoding.py   Wrapper Google Geocoding
    optimizer.py   optimize_by_distance / optimize_by_sector
  routers/
    addresses.py
    routes.py
static/
  index.html
  css/styles.css
  js/app.js, map.js, input.js
tests/
```
