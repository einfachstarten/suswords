// sw.js - Minimaler, stabiler Service Worker für SusWords

const CACHE_NAME = 'suswords-v' + (new URLSearchParams(location.search).get('v') || Date.now());

// Install Event - Sofort aktivieren
self.addEventListener('install', (event) => {
  console.log('[SW] Installing minimal Service Worker...');
  event.waitUntil(self.skipWaiting());
});

// Activate Event - Übernehme sofort alle Tabs
self.addEventListener('activate', (event) => {
  console.log('[SW] Activating minimal Service Worker...');
  event.waitUntil(
    (async () => {
      // Alle Clients übernehmen
      await clients.claim();

      // Alte Caches aufräumen
      const cacheNames = await caches.keys();
      const oldCaches = cacheNames.filter(name =>
        name.startsWith('suswords-') && name !== CACHE_NAME
      );

      if (oldCaches.length > 0) {
        console.log('[SW] Cleaning old caches:', oldCaches);
        await Promise.all(oldCaches.map(name => caches.delete(name)));
      }
    })()
  );
});

// Fetch Event - Einfache, robuste Strategie
self.addEventListener('fetch', (event) => {
  const request = event.request;
  const url = new URL(request.url);

  // Nur HTTP/HTTPS und GET requests behandeln
  if (!url.protocol.startsWith('http') || request.method !== 'GET') {
    return;
  }

  // API Calls nicht cachen (immer fresh)
  if (url.pathname.includes('/api/') ||
      url.pathname.includes('/game_state/') ||
      url.pathname.includes('/vote_') ||
      url.pathname.includes('/debug') ||
      url.pathname.includes('/create_game') ||
      url.pathname.includes('/join_game')) {
    return;
  }

  // Einfache Strategie: Network-first mit Cache-Fallback
  event.respondWith(
    (async () => {
      try {
        // Versuche Netzwerk zuerst
        const networkResponse = await fetch(request);

        // NUR erfolgreiche, komplette Responses cachen
        if (networkResponse.ok &&
            networkResponse.status === 200 &&
            networkResponse.type === 'basic') {

          // Versionierte Assets länger cachen
          if (url.searchParams.has('v')) {
            try {
              const cache = await caches.open(CACHE_NAME);
              await cache.put(request, networkResponse.clone());
              console.log('[SW] Cached versioned asset:', url.pathname);
            } catch (cacheError) {
              // Cache-Fehler ignorieren, nicht crashen
              console.warn('[SW] Cache failed:', cacheError.message);
            }
          }
        }

        return networkResponse;

      } catch (networkError) {
        // Netzwerk fehlgeschlagen - versuche Cache
        console.log('[SW] Network failed, trying cache for:', url.pathname);

        const cachedResponse = await caches.match(request);
        if (cachedResponse) {
          console.log('[SW] Serving from cache:', url.pathname);
          return cachedResponse;
        }

        // Kein Cache verfügbar - Fehler weiterreichen
        throw networkError;
      }
    })()
  );
});

// Message Handler für Version-Updates
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'CHECK_VERSION') {
    event.ports[0].postMessage({
      type: 'VERSION_INFO',
      version: CACHE_NAME
    });
  }

  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});

console.log('[SW] Minimal Service Worker loaded successfully with cache:', CACHE_NAME);