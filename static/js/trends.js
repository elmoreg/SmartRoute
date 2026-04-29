// Renders the Trends tab using last-N-days aggregates from the API.

let charts = {};

function destroyAll() {
  Object.values(charts).forEach(c => c?.destroy());
  charts = {};
}

export async function renderTrends() {
  const res = await fetch('/api/sessions/trends?days=14');
  const data = await res.json();
  renderSummary(data);
  destroyAll();
  charts.quality = lineChart(
    document.getElementById('trend-quality'),
    data.days.map(d => d.date.slice(5)),
    data.days.map(d => d.sessions ? d.quality_score : null),
    '#7c4dff', { suggestedMax: 100 },
  );
  charts.deep = barChart(
    document.getElementById('trend-deep'),
    data.days.map(d => d.date.slice(5)),
    data.days.map(d => d.deep_sleep_min),
    '#22d3ee',
  );
  charts.snores = barChart(
    document.getElementById('trend-snores'),
    data.days.map(d => d.date.slice(5)),
    data.days.map(d => d.snore_events),
    '#ef4444',
  );
}

function renderSummary(data) {
  const el = document.getElementById('trends-summary');
  el.innerHTML = `
    <div><span class="label">Noches registradas</span><span>${data.nights_tracked}</span></div>
    <div><span class="label">Calidad media</span><span>${data.avg_quality}/100</span></div>
    <div><span class="label">Duración media</span><span>${fmtMin(data.avg_duration_min)}</span></div>
    <div><span class="label">Profundo medio</span><span>${fmtMin(data.avg_deep_min)}</span></div>
    <div><span class="label">Ronquidos totales</span><span>${data.total_snore_events}</span></div>
  `;
}

function lineChart(canvas, labels, data, color, scaleOpts = {}) {
  return new Chart(canvas, {
    type: 'line',
    data: {
      labels,
      datasets: [{
        data,
        borderColor: color,
        backgroundColor: color + '33',
        tension: 0.3,
        spanGaps: true,
        pointRadius: 4,
        fill: true,
      }],
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color: '#8a92c8' }, grid: { color: 'rgba(255,255,255,0.05)' } },
        y: { ticks: { color: '#8a92c8' }, grid: { color: 'rgba(255,255,255,0.05)' }, ...scaleOpts },
      },
    },
  });
}

function barChart(canvas, labels, data, color) {
  return new Chart(canvas, {
    type: 'bar',
    data: { labels, datasets: [{ data, backgroundColor: color + 'aa', borderRadius: 4 }] },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color: '#8a92c8' }, grid: { display: false } },
        y: { ticks: { color: '#8a92c8' }, grid: { color: 'rgba(255,255,255,0.05)' }, beginAtZero: true },
      },
    },
  });
}

function fmtMin(total) {
  const h = Math.floor(total / 60);
  const m = Math.round(total % 60);
  return h > 0 ? `${h}h ${m}m` : `${m}m`;
}
