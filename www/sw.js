const CACHE_NAME = 'laopodada-v1.1';
const STATIC_ASSETS = [
  '/',
  '/index.html',
  '/css/app.css',
  '/css/main-page.css',
  '/css/recommend.css',
  '/css/ai-fab.css',
  '/js/config.js',
  '/js/utils.js',
  '/js/api.js',
  '/js/app.js',
  '/js/main-page.js',
  '/js/wardrobe.js',
  '/js/recommend.js',
  '/js/recipe.js',
  '/js/health.js',
  '/js/chat.js',
  '/js/profile.js',
  '/js/ai-fab.js',
];

// Install: pre-cache static assets
self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(STATIC_ASSETS))
  );
  self.skipWaiting();
});

// Activate: remove old caches
self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

// Fetch: Network-first for API, Cache-first for static
self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);

  // API requests: network-first, fallback to cache
  if (url.pathname.startsWith('/api/')) {
    e.respondWith(
      fetch(e.request).catch(() => caches.match(e.request))
    );
    return;
  }

  // Images: network-first with cache fallback
  if (e.request.destination === 'image') {
    e.respondWith(
      fetch(e.request).then(resp => {
        const clone = resp.clone();
        caches.open(CACHE_NAME).then(cache => cache.put(e.request, clone));
        return resp;
      }).catch(() => caches.match(e.request))
    );
    return;
  }

  // Static assets: cache-first, network fallback
  e.respondWith(
    caches.match(e.request).then(cached => {
      if (cached) return cached;
      return fetch(e.request).then(resp => {
        if (resp.ok && url.origin === self.location.origin) {
          const clone = resp.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(e.request, clone));
        }
        return resp;
      });
    })
  );
});
