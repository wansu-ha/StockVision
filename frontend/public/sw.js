/** Service Worker — 네트워크 퍼스트 캐시. */

const CACHE_NAME = 'sv-cache-v1'

self.addEventListener('install', () => {
  self.skipWaiting()
})

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((names) =>
      Promise.all(
        names.filter((n) => n !== CACHE_NAME).map((n) => caches.delete(n))
      )
    )
  )
  self.clients.claim()
})

self.addEventListener('fetch', (event) => {
  // GET 이외, API, WS 요청은 캐시하지 않음
  if (event.request.method !== 'GET') return
  if (event.request.url.includes('/api/') || event.request.url.includes('/ws/')) {
    return
  }

  event.respondWith(
    fetch(event.request)
      .then((response) => {
        const clone = response.clone()
        caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone))
        return response
      })
      .catch(() => caches.match(event.request).then((r) => r || new Response('Offline', { status: 503 })))
  )
})
