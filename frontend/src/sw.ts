/// <reference lib="webworker" />
/* eslint-disable @typescript-eslint/no-explicit-any */
import { precacheAndRoute, matchPrecache } from 'workbox-precaching';
import { registerRoute, NavigationRoute } from 'workbox-routing';
import { CacheFirst, StaleWhileRevalidate } from 'workbox-strategies';
import { ExpirationPlugin } from 'workbox-expiration';
import { RangeRequestsPlugin } from 'workbox-range-requests';
import { CacheableResponsePlugin } from 'workbox-cacheable-response';

declare const self: ServiceWorkerGlobalScope & { __WB_MANIFEST: any[] };

// Take control immediately (critical for iOS Safari — without this,
// the SW isn't the controller until the next navigation)
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', (event) => event.waitUntil(self.clients.claim()));

// Precache Vite build assets (auto-injected by vite-plugin-pwa)
precacheAndRoute(self.__WB_MANIFEST);

// Navigation requests: try network, fall back to precached index.html (SPA shell).
// This ensures ANY route (e.g. /s/abc123) works offline — React Router handles routing
// client-side once the app shell loads.
registerRoute(
  new NavigationRoute(async () => {
    try {
      const response = await fetch(new Request(new URL('/', self.location.origin)));
      if (response.ok) return response;
    } catch {
      // Network failed — expected when offline
    }
    // Fall back to precached index.html
    const cached = await matchPrecache('/index.html');
    if (cached) return cached;
    return new Response('Offline', { status: 503 });
  })
);

// Google Fonts stylesheets
registerRoute(
  ({ url }: { url: URL }) => url.origin === 'https://fonts.googleapis.com',
  new StaleWhileRevalidate({
    cacheName: 'google-fonts-stylesheets',
  })
);

// Google Fonts webfont files
registerRoute(
  ({ url }: { url: URL }) => url.origin === 'https://fonts.gstatic.com',
  new CacheFirst({
    cacheName: 'google-fonts-webfonts',
    plugins: [
      new CacheableResponsePlugin({ statuses: [0, 200] }),
      new ExpirationPlugin({ maxEntries: 30, maxAgeSeconds: 365 * 24 * 60 * 60 }),
    ],
  })
);

// Story metadata: StaleWhileRevalidate for instant offline + background refresh
registerRoute(
  ({ url }: { url: URL }) => url.pathname.match(/^\/api\/permalink\/[^/]+$/) !== null,
  new StaleWhileRevalidate({
    cacheName: 'story-metadata',
    plugins: [
      new CacheableResponsePlugin({ statuses: [0, 200] }),
      new ExpirationPlugin({ maxEntries: 50, maxAgeSeconds: 30 * 24 * 60 * 60 }),
    ],
  })
);

// Story audio: CacheFirst with range request support (critical for iOS Safari)
// Accept 200 AND 206 — Safari always sends range requests for <audio> elements
registerRoute(
  ({ url }: { url: URL }) => url.pathname.match(/^\/api\/permalink\/[^/]+\/audio$/) !== null,
  new CacheFirst({
    cacheName: 'story-audio',
    plugins: [
      new CacheableResponsePlugin({ statuses: [0, 200, 206] }),
      new RangeRequestsPlugin(),
      new ExpirationPlugin({ maxEntries: 20, maxAgeSeconds: 30 * 24 * 60 * 60 }),
    ],
  })
);

// Illustration images: CacheFirst (immutable once generated)
registerRoute(
  ({ url }: { url: URL }) => url.pathname.startsWith('/storage/stories/') && url.pathname.endsWith('.png'),
  new CacheFirst({
    cacheName: 'story-illustrations',
    plugins: [
      new CacheableResponsePlugin({ statuses: [0, 200] }),
      new ExpirationPlugin({ maxEntries: 200, maxAgeSeconds: 30 * 24 * 60 * 60 }),
    ],
  })
);

// Prefetch audio for offline: the app sends a message after loading a story page.
// We fetch the full file (no Range header) so it's cached as a 200 response,
// which the RangeRequestsPlugin can then slice for Safari's range requests offline.
self.addEventListener('message', (event: ExtendableMessageEvent) => {
  if (event.data?.type === 'PREFETCH_AUDIO' && event.data.url) {
    const audioUrl = event.data.url;
    event.waitUntil(
      caches.open('story-audio').then(async (cache) => {
        const existing = await cache.match(audioUrl);
        if (existing) {
          // Already cached — notify immediately
          notifyClients('AUDIO_CACHED', audioUrl);
          return;
        }
        try {
          const response = await fetch(audioUrl);
          if (response.ok) {
            await cache.put(audioUrl, response);
            notifyClients('AUDIO_CACHED', audioUrl);
          }
        } catch {
          // Best-effort prefetch
        }
      })
    );
  }
});

async function notifyClients(type: string, url: string) {
  const clients = await self.clients.matchAll({ type: 'window' });
  for (const client of clients) {
    client.postMessage({ type, url });
  }
}
