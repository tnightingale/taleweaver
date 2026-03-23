/// <reference lib="webworker" />
/* eslint-disable @typescript-eslint/no-explicit-any */
import { precacheAndRoute } from 'workbox-precaching';
import { registerRoute, NavigationRoute } from 'workbox-routing';
import { CacheFirst, NetworkFirst, StaleWhileRevalidate } from 'workbox-strategies';
import { ExpirationPlugin } from 'workbox-expiration';
import { RangeRequestsPlugin } from 'workbox-range-requests';
import { CacheableResponsePlugin } from 'workbox-cacheable-response';

declare const self: ServiceWorkerGlobalScope & { __WB_MANIFEST: any[] };

// Precache Vite build assets (auto-injected by vite-plugin-pwa)
precacheAndRoute(self.__WB_MANIFEST);

// Navigation requests: NetworkFirst, falling back to cached app shell
const navigationHandler = new NetworkFirst({
  cacheName: 'navigation',
  networkTimeoutSeconds: 3,
});
registerRoute(new NavigationRoute(navigationHandler));

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
        if (existing) return;
        try {
          const response = await fetch(audioUrl);
          if (response.ok) {
            await cache.put(audioUrl, response);
          }
        } catch {
          // Best-effort prefetch
        }
      })
    );
  }
});
