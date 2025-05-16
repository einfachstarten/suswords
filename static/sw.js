self.addEventListener('install', event => {
  console.log('Service Worker installiert');
  self.skipWaiting();
});

self.addEventListener('fetch', function(event) {
  // Nur durchreichen (später: caching möglich)
});