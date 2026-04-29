// Minimal cache-first service worker for the NightOwl shell.
const CACHE = 'nightowl-v1';
const SHELL = [
  '/',
  '/static/css/styles.css',
  '/static/js/app.js',
  '/static/js/recorder.js',
  '/static/js/analyzer.js',
  '/static/js/charts.js',
  '/static/manifest.webmanifest',
  '/static/icon.svg',
  'https://cdn.jsdelivr.net/npm/chart.js@4.4.4/dist/chart.umd.min.js',
];

self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (e) => {
  const req = e.request;
  if (req.method !== 'GET') return;
  // Network-first for API; cache-first for shell.
  if (new URL(req.url).pathname.startsWith('/api/')) {
    e.respondWith(fetch(req).catch(() => caches.match(req)));
    return;
  }
  e.respondWith(
    caches.match(req).then(hit => hit || fetch(req).then(res => {
      const copy = res.clone();
      caches.open(CACHE).then(c => c.put(req, copy)).catch(() => {});
      return res;
    }).catch(() => caches.match('/')))
  );
});
