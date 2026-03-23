/// <reference lib="webworker" />
/* eslint-disable @typescript-eslint/no-explicit-any */
import { precacheAndRoute } from 'workbox-precaching';
import { registerRoute } from 'workbox-routing';
import { CacheFirst, StaleWhileRevalidate } from 'workbox-strategies';
import { ExpirationPlugin } from 'workbox-expiration';
import { RangeRequestsPlugin } from 'workbox-range-requests';
import { CacheableResponsePlugin } from 'workbox-cacheable-response';

declare const self: ServiceWorkerGlobalScope & { __WB_MANIFEST: any[] };

// Version tied to the build — changes whenever SW content changes (new precache hashes).
// Old app-shell caches are cleaned up on activate so stale HTML can't reference
// JS/CSS bundles that no longer exist in the new precache.
const APP_SHELL_CACHE = 'app-shell';
const EXPECTED_CACHES = new Set([APP_SHELL_CACHE, 'google-fonts-stylesheets', 'google-fonts-webfonts', 'story-metadata', 'story-audio', 'story-illustrations']);

// ============================================================================
// Lifecycle: install + activate
// ============================================================================

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(APP_SHELL_CACHE).then((cache) =>
      // Cache fresh app shell HTML — references the current build's JS/CSS hashes
      cache.addAll(['/', '/index.html'])
    )
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    Promise.all([
      self.clients.claim(),
      // Clean up old Workbox precache versions — they hold stale JS/CSS bundles.
      // Our runtime caches (story-metadata, story-audio, etc.) are kept.
      caches.keys().then((names) =>
        Promise.all(
          names
            .filter((name) => !EXPECTED_CACHES.has(name))
            .map((name) => caches.delete(name))
        )
      ),
    ])
  );
});

// Precache Vite build assets (JS, CSS, images) for instant loading
precacheAndRoute(self.__WB_MANIFEST);

// ============================================================================
// Navigation: raw fetch handler (runs BEFORE Workbox's router)
// Serves the app shell for ALL navigation requests.
// This is more reliable than Workbox's NavigationRoute on iOS Safari.
// ============================================================================

self.addEventListener('fetch', (event) => {
  if (event.request.mode !== 'navigate') return;

  event.respondWith(
    (async () => {
      try {
        // Online: fetch from network and update the cached shell
        const response = await fetch(event.request);
        if (response.ok) {
          const cache = await caches.open(APP_SHELL_CACHE);
          cache.put(event.request, response.clone());
        }
        return response;
      } catch {
        // Offline: serve from our app-shell cache
        const cached =
          await caches.match(event.request) ||
          await caches.match('/index.html') ||
          await caches.match('/');
        if (cached) return cached;
        return new Response('Offline', { status: 503, headers: { 'Content-Type': 'text/html' } });
      }
    })()
  );
});

// ============================================================================
// Runtime caching (Workbox handles non-navigation requests)
// ============================================================================

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

// ============================================================================
// Audio prefetch messaging
// ============================================================================

self.addEventListener('message', (event: ExtendableMessageEvent) => {
  if (event.data?.type === 'PREFETCH_AUDIO' && event.data.url) {
    const audioUrl = event.data.url;
    event.waitUntil(
      caches.open('story-audio').then(async (cache) => {
        const existing = await cache.match(audioUrl);
        if (existing) {
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
