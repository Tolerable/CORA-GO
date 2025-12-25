/**
 * CORA-GO Service Worker
 * Enables offline support and PWA features
 */

const CACHE_NAME = 'cora-go-v1';
const ASSETS = [
    '/',
    '/index.html',
    '/css/cora-go.css',
    '/js/app.js',
    '/manifest.json'
];

// Install - cache assets
self.addEventListener('install', (e) => {
    e.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => cache.addAll(ASSETS))
            .then(() => self.skipWaiting())
    );
});

// Activate - clean old caches
self.addEventListener('activate', (e) => {
    e.waitUntil(
        caches.keys().then(keys => {
            return Promise.all(
                keys.filter(k => k !== CACHE_NAME)
                    .map(k => caches.delete(k))
            );
        }).then(() => self.clients.claim())
    );
});

// Fetch - network first, cache fallback
self.addEventListener('fetch', (e) => {
    // Skip non-GET requests
    if (e.request.method !== 'GET') return;

    // Skip API calls (Ollama, Pollinations)
    if (e.request.url.includes('localhost:11434') ||
        e.request.url.includes('pollinations.ai')) {
        return;
    }

    e.respondWith(
        fetch(e.request)
            .then(response => {
                // Clone and cache successful responses
                if (response.ok) {
                    const clone = response.clone();
                    caches.open(CACHE_NAME)
                        .then(cache => cache.put(e.request, clone));
                }
                return response;
            })
            .catch(() => {
                // Fallback to cache
                return caches.match(e.request);
            })
    );
});
