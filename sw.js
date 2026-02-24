// Service Worker COMPLETELY DISABLED - causing network errors
// This file does nothing and lets all requests pass through

self.addEventListener('install', function(event) {
  console.log('Service Worker installed but disabled');
});

self.addEventListener('fetch', function(event) {
  // Don't intercept anything - let all requests pass through
  event.respondWith(fetch(event.request));
});

self.addEventListener('activate', function(event) {
  event.waitUntil(
    caches.keys().then(function(cacheNames) {
      return Promise.all(
        cacheNames.map(function(cacheName) {
          // Delete all caches
          return caches.delete(cacheName);
        })
      );
    })
  );
});
