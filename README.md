# NightOwl — Sleep Tracker

PWA para medir sueño, calidad, momentos de sueño profundo y ronquidos. Se instala localmente: el análisis de audio y movimiento corre **en el dispositivo** (no se sube audio a ningún servidor — solo agregados por minuto).

## Características

- **Grabación de sesión**: un botón grande inicia/termina el seguimiento nocturno.
- **Detección de ronquidos** vía Web Audio API: analiza la razón de energía de baja frecuencia (80–500 Hz) para clasificar ronquidos en tiempo real. Sensibilidad ajustable.
- **Fases de sueño** (profundo / ligero / despierto) estimadas con actigrafía usando `DeviceMotionEvent` + suavizado por votación mayoritaria.
- **Puntaje de calidad 0–100** combinando eficiencia, ratio de sueño profundo, penalización por ronquidos y ruido.
- **Vista en vivo** con ruido, movimiento, fase actual y gráfico del último minuto.
- **Historial persistente** en SQLite con hipnograma y cronología de ronquidos por sesión.
- **PWA instalable**: manifest + service worker, funciona offline tras la primera carga.
- **Wake Lock** durante la grabación para evitar que el teléfono suspenda y corte el seguimiento.
- **Alarma inteligente**: si configuras una hora objetivo, suena al detectar fase ligera dentro de los 30 min anteriores (evita despertar en sueño profundo).
- **Exportar CSV** de la sesión desde la vista de detalle.

## Stack

- **Backend**: FastAPI + SQLModel (SQLite)
- **Frontend**: HTML + JS vanilla (módulos ES) + Chart.js
- **Audio/Motion**: Web Audio API (`AnalyserNode` / FFT) + `DeviceMotionEvent`
- **Persistencia**: por-minuto, no se almacena audio crudo

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
uvicorn app.main:app --reload
```

Abre http://localhost:8000. Para acceder al micrófono y al sensor de movimiento en iOS/Android modernos, necesitas **HTTPS** (o `localhost`).

### Uso

1. Pestaña **Grabar** → "Empezar a dormir" (acepta permisos de mic y movimiento).
2. Deja el teléfono sobre el colchón cerca de la almohada.
3. Al despertar, "Terminar" → la sesión se guarda y se abre el resumen.
4. Pestaña **Historial** para revisar noches anteriores.

## Tests

```bash
pytest
```

Cubre clasificación de fases, suavizado, score de calidad, contador de eventos de ronquido, y los endpoints de sesiones.

## Estructura

```
app/
  main.py              FastAPI + lifespan
  config.py            Variables de entorno
  database.py          Engine + init_db
  models.py            SQLModel: SleepSession, SleepSample
  schemas.py           Pydantic I/O
  routers/sessions.py  CRUD /api/sessions
  services/analyzer.py Fase + score (usado por backend y reflejado en JS)
static/
  index.html
  css/styles.css
  js/
    app.js       Orquestador (tabs, grabación, historial, export CSV, wake lock)
    recorder.js  SleepRecorder: micro + motion, 1 muestra/min
    analyzer.js  Clasificación en vivo (espejo de analyzer.py)
    charts.js    Hipnograma + cronología de ruido
    alarm.js     Alarma inteligente con tono Web Audio
  manifest.webmanifest
  sw.js          Service worker (cache shell + network-first API)
tests/
  test_analyzer.py
  test_api.py
```

## Privacidad

El audio nunca sale del dispositivo. Solo se guardan por minuto: nivel de ruido relativo (dB proxy), magnitud de movimiento normalizada y un booleano de ronquido detectado.

## Roadmap

- Modelo ML on-device (TensorFlow.js YAMNet) para mejorar detección de ronquidos.
- Sincronización multi-dispositivo (Supabase o similar).
- Tendencias semanales y comparativas entre noches.
- Importar grabación de audio para análisis post-hoc.
