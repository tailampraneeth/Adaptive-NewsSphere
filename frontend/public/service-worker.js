const CACHE_NAME = 'heimdall-static-v1';
const STORY_CACHE_NAME = 'heimdall-stories-v1';

const STATIC_ASSETS = [
  '/',
  '/index.html',
  '/manifest.json'
];

// Install Event - Pre-cache shell assets
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(STATIC_ASSETS);
    })
  );
  self.skipWaiting();
});

// Activate Event - Clean old caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((key) => {
          if (key !== CACHE_NAME && key !== STORY_CACHE_NAME) {
            return caches.delete(key);
          }
        })
      );
    })
  );
  self.clients.claim();
});

// Fetch Event - Dynamic caching with LRU limit
self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // Focus on API story retrieval requests
  if (event.request.method === 'GET' && url.pathname.includes('/api/v1/stories/')) {
    event.respondWith(
      fetch(event.request)
        .then((response) => {
          if (!response || response.status !== 200) {
            return response;
          }
          
          const responseToCache = response.clone();
          caches.open(STORY_CACHE_NAME).then((cache) => {
            cache.put(event.request, responseToCache);
            // Limit cache to 20 items (LRU eviction)
            limitCacheSize(STORY_CACHE_NAME, 20);
          });
          
          return response;
        })
        .catch(() => {
          return caches.match(event.request);
        })
    );
    return;
  }

  // Shell assets & general caching
  event.respondWith(
    caches.match(event.request).then((cachedResponse) => {
      if (cachedResponse) {
        return cachedResponse;
      }
      return fetch(event.request);
    })
  );
});

// Helper to limit cache size
function limitCacheSize(cacheName, maxItems) {
  caches.open(cacheName).then((cache) => {
    cache.keys().then((requests) => {
      if (requests.length > maxItems) {
        cache.delete(requests[0]).then(() => {
          limitCacheSize(cacheName, maxItems);
        });
      }
    });
  });
}
