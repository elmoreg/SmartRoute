import { SleepRecorder } from './recorder.js';
import { classifyPhase, PHASE_LABEL } from './analyzer.js';
import { initLiveChart, pushLivePoint, renderHypnogram, renderNoiseChart } from './charts.js';
import { SmartAlarm } from './alarm.js';

const $ = (sel) => document.querySelector(sel);

const state = {
  recorder: null,
  timer: null,
  wakeLock: null,
  alarm: new SmartAlarm(),
  currentDetail: null,
};

// ---- tabs ----
document.querySelectorAll('.tab').forEach(btn => {
  btn.addEventListener('click', () => activateTab(btn.dataset.tab));
});

function activateTab(name) {
  document.querySelectorAll('.tab').forEach(t => t.classList.toggle('active', t.dataset.tab === name));
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.toggle('active', p.id === `tab-${name}`));
  if (name === 'history') loadHistory();
  if (name === 'live' && state.recorder) {
    setTimeout(() => initLiveChart(document.getElementById('live-chart')), 0);
  }
}

// ---- threshold + alarm config ----
const slider = $('#snore-threshold');
const sliderVal = $('#snore-threshold-val');
slider.addEventListener('input', () => {
  sliderVal.textContent = slider.value;
  if (state.recorder) state.recorder.setSnoreThreshold(+slider.value);
});

const alarmInput = $('#alarm-time');
alarmInput.addEventListener('change', () => state.alarm.set(alarmInput.value));

// ---- toggle record ----
$('#btn-toggle').addEventListener('click', async () => {
  if (!state.recorder || !state.recorder.running) {
    await startRecording();
  } else {
    await stopRecording();
  }
});

async function startRecording() {
  const rec = new SleepRecorder({ snoreThreshold: +slider.value });
  state.recorder = rec;
  state.alarm.set(alarmInput.value);

  rec.addEventListener('tick', (e) => {
    updateLive(e.detail);
    if (state.alarm.shouldFire(e.detail)) state.alarm.fire(() => stopRecording());
  });
  rec.addEventListener('stopped', (e) => handleStopped(e.detail));

  try {
    if (typeof DeviceMotionEvent !== 'undefined' && typeof DeviceMotionEvent.requestPermission === 'function') {
      const p = await DeviceMotionEvent.requestPermission();
      if (p !== 'granted') console.warn('Motion permission denied');
    }
    await rec.start();
    await acquireWakeLock();
  } catch (err) {
    alert('No se pudo iniciar la grabación: ' + err.message);
    state.recorder = null;
    return;
  }

  $('#btn-toggle').textContent = 'Terminar';
  $('#btn-toggle').classList.add('recording');
  $('#status').textContent = 'Grabando';
  $('#status').classList.add('recording');
  state.timer = setInterval(tickElapsed, 1000);
  initLiveChart(document.getElementById('live-chart'));
}

async function stopRecording() {
  if (!state.recorder) return;
  await state.recorder.stop();
  await releaseWakeLock();
  clearInterval(state.timer);
  $('#btn-toggle').textContent = 'Empezar a dormir';
  $('#btn-toggle').classList.remove('recording');
  $('#status').textContent = 'Detenido';
  $('#status').classList.remove('recording');
}

async function acquireWakeLock() {
  if (!('wakeLock' in navigator)) return;
  try {
    state.wakeLock = await navigator.wakeLock.request('screen');
    document.addEventListener('visibilitychange', reacquireWakeLock);
  } catch (err) {
    console.warn('Wake Lock unavailable:', err.message);
  }
}

async function reacquireWakeLock() {
  if (document.visibilityState === 'visible' && state.recorder?.running && !state.wakeLock) {
    try { state.wakeLock = await navigator.wakeLock.request('screen'); } catch {}
  }
}

async function releaseWakeLock() {
  document.removeEventListener('visibilitychange', reacquireWakeLock);
  if (state.wakeLock) {
    try { await state.wakeLock.release(); } catch {}
    state.wakeLock = null;
  }
}

function tickElapsed() {
  if (!state.recorder || !state.recorder.startedAt) return;
  const ms = Date.now() - state.recorder.startedAt.getTime();
  $('#elapsed').textContent = fmtDuration(ms);
}

function updateLive(snap) {
  $('#live-noise').textContent = snap.noise.toFixed(0);
  $('#live-motion').textContent = snap.motion.toFixed(2);
  $('#live-snore').textContent = snap.snoring ? 'Sí' : 'No';
  const phase = classifyPhase({ motion: snap.motion, noise_db: snap.noise, snoring: snap.snoring });
  $('#live-phase').textContent = PHASE_LABEL[phase];
  pushLivePoint(snap.minute + 'm', snap.noise, snap.motion);
}

async function handleStopped({ startedAt, endedAt, samples }) {
  if (samples.length === 0) {
    alert('Sesión demasiado corta para analizar.');
    state.recorder = null;
    return;
  }
  try {
    const res = await fetch('/api/sessions', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        started_at: startedAt.toISOString(),
        ended_at: endedAt.toISOString(),
        samples,
      }),
    });
    if (!res.ok) throw new Error(await res.text());
    const saved = await res.json();
    state.recorder = null;
    activateTab('history');
    showDetail(saved);
  } catch (err) {
    alert('Error al guardar: ' + err.message);
  }
}

// ---- history ----
async function loadHistory() {
  $('#history-detail').classList.add('hidden');
  const listEl = $('#history-list');
  listEl.classList.remove('hidden');
  const res = await fetch('/api/sessions');
  const items = await res.json();
  if (items.length === 0) {
    listEl.innerHTML = '<div class="empty">Aún no hay sesiones registradas.</div>';
    return;
  }
  listEl.innerHTML = items.map(renderHistoryItem).join('');
  listEl.querySelectorAll('[data-id]').forEach(el => {
    el.addEventListener('click', async () => {
      const res = await fetch(`/api/sessions/${el.dataset.id}`);
      const detail = await res.json();
      showDetail(detail);
    });
  });
}

function renderHistoryItem(s) {
  const date = new Date(s.started_at);
  const label = date.toLocaleDateString('es', { weekday: 'short', day: 'numeric', month: 'short' });
  const time = date.toLocaleTimeString('es', { hour: '2-digit', minute: '2-digit' });
  const scoreCls = s.quality_score < 40 ? 'low' : s.quality_score < 70 ? 'mid' : '';
  return `
    <div class="history-item" data-id="${s.id}">
      <div>
        <div class="date">${label} · ${time}</div>
        <div class="meta">${fmtMinutes(s.duration_min)} · ${s.snore_events} ronquidos · ${Math.round(s.deep_sleep_min)}min profundo</div>
      </div>
      <div class="score ${scoreCls}">${Math.round(s.quality_score)}</div>
    </div>`;
}

function showDetail(s) {
  state.currentDetail = s;
  $('#history-list').classList.add('hidden');
  $('#history-detail').classList.remove('hidden');
  const date = new Date(s.started_at);
  $('#detail-date').textContent = date.toLocaleString('es', { weekday: 'long', day: 'numeric', month: 'long', hour: '2-digit', minute: '2-digit' });
  $('#detail-score').textContent = Math.round(s.quality_score);
  $('#detail-duration').textContent = fmtMinutes(s.duration_min);
  $('#detail-deep').textContent = fmtMinutes(s.deep_sleep_min);
  $('#detail-light').textContent = fmtMinutes(s.light_sleep_min);
  $('#detail-awake').textContent = fmtMinutes(s.awake_min);
  $('#detail-snores').textContent = `${s.snore_events} (${Math.round(s.snore_total_sec / 60)}min)`;
  renderHypnogram(document.getElementById('hypno-chart'), s.samples);
  renderNoiseChart(document.getElementById('noise-chart'), s.samples);
}

$('#back-btn').addEventListener('click', loadHistory);

$('#export-csv').addEventListener('click', () => {
  if (!state.currentDetail) return;
  const s = state.currentDetail;
  const header = 'minute,phase,motion,noise_db,snoring\n';
  const body = s.samples.map(x =>
    `${x.minute},${x.phase},${x.motion},${x.noise_db},${x.snoring ? 1 : 0}`
  ).join('\n');
  const blob = new Blob([header + body], { type: 'text/csv' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  const stamp = new Date(s.started_at).toISOString().slice(0, 10);
  a.download = `nightowl-${stamp}-${s.id}.csv`;
  a.click();
  URL.revokeObjectURL(url);
});

$('#delete-session').addEventListener('click', async () => {
  if (!state.currentDetail) return;
  if (!confirm('¿Eliminar esta sesión?')) return;
  await fetch(`/api/sessions/${state.currentDetail.id}`, { method: 'DELETE' });
  state.currentDetail = null;
  loadHistory();
});

// ---- utils ----
function fmtDuration(ms) {
  const totalSec = Math.floor(ms / 1000);
  const h = Math.floor(totalSec / 3600);
  const m = Math.floor((totalSec % 3600) / 60);
  const s = totalSec % 60;
  return h > 0
    ? `${h}:${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`
    : `${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`;
}

function fmtMinutes(total) {
  const h = Math.floor(total / 60);
  const m = Math.round(total % 60);
  return h > 0 ? `${h}h ${m}m` : `${m}m`;
}
