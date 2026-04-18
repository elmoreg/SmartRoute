import { phaseToY, PHASE_COLOR } from './analyzer.js';

let liveChart = null;
let hypnoChart = null;
let noiseChart = null;

export function initLiveChart(canvas) {
  if (liveChart) liveChart.destroy();
  liveChart = new Chart(canvas, {
    type: 'line',
    data: {
      labels: [],
      datasets: [
        { label: 'Ruido (dB)', data: [], borderColor: '#22d3ee', backgroundColor: 'rgba(34,211,238,0.1)', tension: 0.3, pointRadius: 0 },
        { label: 'Movimiento ×100', data: [], borderColor: '#f59e0b', backgroundColor: 'rgba(245,158,11,0.1)', tension: 0.3, pointRadius: 0 },
      ],
    },
    options: {
      responsive: true,
      animation: false,
      scales: {
        x: { ticks: { color: '#8a92c8' }, grid: { color: 'rgba(255,255,255,0.05)' } },
        y: { ticks: { color: '#8a92c8' }, grid: { color: 'rgba(255,255,255,0.05)' } },
      },
      plugins: { legend: { labels: { color: '#e8ecff' } } },
    },
  });
  return liveChart;
}

export function pushLivePoint(label, noise, motion) {
  if (!liveChart) return;
  const max = 60;
  liveChart.data.labels.push(label);
  liveChart.data.datasets[0].data.push(noise);
  liveChart.data.datasets[1].data.push(motion * 100);
  if (liveChart.data.labels.length > max) {
    liveChart.data.labels.shift();
    liveChart.data.datasets.forEach(d => d.data.shift());
  }
  liveChart.update('none');
}

export function renderHypnogram(canvas, samples) {
  if (hypnoChart) hypnoChart.destroy();
  const labels = samples.map(s => fmtMin(s.minute));
  const data = samples.map(s => phaseToY(s.phase));
  const colors = samples.map(s => PHASE_COLOR[s.phase]);
  hypnoChart = new Chart(canvas, {
    type: 'line',
    data: {
      labels,
      datasets: [{
        label: 'Fase',
        data,
        borderColor: '#7c4dff',
        backgroundColor: 'rgba(124,77,255,0.15)',
        stepped: true,
        fill: true,
        pointBackgroundColor: colors,
        pointRadius: 3,
      }],
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color: '#8a92c8', maxTicksLimit: 10 }, grid: { color: 'rgba(255,255,255,0.05)' } },
        y: {
          min: 0, max: 2,
          ticks: {
            color: '#8a92c8',
            stepSize: 1,
            callback: (v) => ({ 0: 'Profundo', 1: 'Ligero', 2: 'Despierto' }[v] || ''),
          },
          grid: { color: 'rgba(255,255,255,0.05)' },
        },
      },
    },
  });
}

export function renderNoiseChart(canvas, samples) {
  if (noiseChart) noiseChart.destroy();
  const labels = samples.map(s => fmtMin(s.minute));
  const noise = samples.map(s => s.noise_db);
  const snores = samples.map(s => s.snoring ? s.noise_db : null);
  noiseChart = new Chart(canvas, {
    type: 'line',
    data: {
      labels,
      datasets: [
        { label: 'Ruido (dB)', data: noise, borderColor: '#22d3ee', backgroundColor: 'rgba(34,211,238,0.1)', tension: 0.3, pointRadius: 0, fill: true },
        { label: 'Ronquidos', data: snores, borderColor: '#ef4444', backgroundColor: '#ef4444', showLine: false, pointRadius: 5 },
      ],
    },
    options: {
      responsive: true,
      plugins: { legend: { labels: { color: '#e8ecff' } } },
      scales: {
        x: { ticks: { color: '#8a92c8', maxTicksLimit: 10 }, grid: { color: 'rgba(255,255,255,0.05)' } },
        y: { ticks: { color: '#8a92c8' }, grid: { color: 'rgba(255,255,255,0.05)' } },
      },
    },
  });
}

function fmtMin(m) {
  const h = Math.floor(m / 60);
  const r = m % 60;
  return `${h}h${String(r).padStart(2, '0')}`;
}
