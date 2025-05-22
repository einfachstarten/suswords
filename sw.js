const CACHE_VERSION = 'v1.1';
const CACHE_NAME = `suswords-cache-${CACHE_VERSION}`;
const OFFLINE_URL = '/';

const STATIC_ASSETS = [
  '/',
  '/static/suswords.png',
  '/static/suswords_splash.png',
  '/static/suswords_icon192.png',
  '/static/suswords_icon512.png',
  '/static/suswords.mp3',
  '/static/favicon.ico',
  '/create',
  '/static/manifest.json'
];

// Installation: Cache wichtige Assets
self.addEventListener('install', event => {
  console.log('Service Worker wird installiert (Version ' + CACHE_VERSION + ')');
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('Assets werden gecached');
        return cache.addAll(STATIC_ASSETS);
      })
      .then(() => self.skipWaiting())
  );
});

// Aktivierung: Alte Caches löschen
self.addEventListener('activate', event => {
  console.log('Service Worker aktiviert (Version ' + CACHE_VERSION + ')');
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.filter(cacheName => {
          return cacheName.startsWith('suswords-cache-') && cacheName !== CACHE_NAME;
        }).map(cacheName => {
          console.log('Alte Cache-Version wird gelöscht:', cacheName);
          return caches.delete(cacheName);
        })
      );
    }).then(() => {
      console.log('Service Worker übernimmt sofort die Kontrolle');
      return self.clients.claim();
    })
  );
});

// Verbesserte Fetch-Strategie mit Netzwerkpriorität für API-Aufrufe
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);

  // API-Anfragen immer vom Netzwerk
  if (url.pathname.includes('/api/') ||
      url.pathname.includes('game_state') ||
      url.pathname.includes('players_in_game') ||
      url.pathname.includes('join_game') ||
      url.pathname.includes('submit_word') ||
      url.pathname.includes('start_vote') ||
      url.pathname.includes('cast_vote') ||
      event.request.method !== 'GET') {

    return event.respondWith(
      fetch(event.request).catch(error => {
        console.log('Netzwerkfehler, kann keine API-Anfrage ausführen', error);
        return new Response(JSON.stringify({
          error: 'Offline-Modus: Kann keine Verbindung zum Server herstellen.'
        }), {
          status: 503,
          headers: { 'Content-Type': 'application/json' }
        });
      })
    );
  }

  // Für statische Assets: Cache-First-Strategie
  event.respondWith(
    caches.match(event.request)
      .then(response => {
        if (response) {
          console.log('Aus Cache bedient:', event.request.url);
          return response;
        }

        console.log('Nicht im Cache gefunden, lade vom Netzwerk:', event.request.url);
        return fetch(event.request).then(networkResponse => {
          // Nur GET-Anfragen und erfolgreiche Antworten cachen
          if (event.request.method !== 'GET' ||
              !networkResponse ||
              networkResponse.status !== 200 ||
              networkResponse.type !== 'basic') {
            return networkResponse;
          }

          // Wichtig: Response klonen, da wir es zweimal verbrauchen
          var responseToCache = networkResponse.clone();

          caches.open(CACHE_NAME)
            .then(cache => {
              console.log('Neue Ressource wird dem Cache hinzugefügt:', event.request.url);
              cache.put(event.request, responseToCache);
            });

          return networkResponse;
        });
      })
      .catch(error => {
        console.log('Fetch fehlgeschlagen:', error);

        // Für Navigations-Anfragen: Offline-Seite anzeigen
        if (event.request.mode === 'navigate') {
          return caches.match(OFFLINE_URL);
        }

        // Für andere Anfragen: Fehler zurückgeben
        return new Response('Offline: Ressource nicht verfügbar', {
          status: 503,
          statusText: 'Service Unavailable'
        });
      })
  );
});

// Periodische Synchronisation (falls unterstützt)
self.addEventListener('periodicsync', event => {
  if (event.tag === 'update-cache') {
    event.waitUntil(updateCache());
  }
});

// Funktion zum Aktualisieren des Caches
async function updateCache() {
  const cache = await caches.open(CACHE_NAME);

  // Hauptassets immer aktualisieren
  for (const url of STATIC_ASSETS) {
    try {
      const response = await fetch(url);
      if (response.ok) {
        await cache.put(url, response);
        console.log('Asset aktualisiert:', url);
      }
    } catch (error) {
      console.error('Fehler beim Aktualisieren des Assets:', url, error);
    }
  }
}