/// <reference lib="webworker" />
/* eslint-disable @typescript-eslint/no-explicit-any */
import { precache } from 'workbox-precaching';
import { registerRoute } from 'workbox-routing';
import { CacheFirst, StaleWhileRevalidate } from 'workbox-strategies';
import { ExpirationPlugin } from 'workbox-expiration';
import { RangeRequestsPlugin } from 'workbox-range-requests';
import { CacheableResponsePlugin } from 'workbox-cacheable-response';

declare const self: ServiceWorkerGlobalScope & { __WB_MANIFEST: any[] };

const APP_SHELL_CACHE = 'app-shell';
const EXPECTED_CACHES = new Set([
  APP_SHELL_CACHE,
  'google-fonts-stylesheets', 'google-fonts-webfonts',
  'story-metadata', 'story-audio', 'story-illustrations',
]);

// ============================================================================
// Lifecycle
// ============================================================================

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(APP_SHELL_CACHE).then((cache) =>
      cache.addAll(['/', '/index.html'])
    )
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    Promise.all([
      self.clients.claim(),
      // Remove stale caches (old Workbox precache versions, etc.)
      // Clean up old caches, but keep Workbox precache (starts with 'workbox-precache')
      // and our expected runtime caches
      caches.keys().then((names) =>
        Promise.all(
          names
            .filter((name) => !EXPECTED_CACHES.has(name) && !name.startsWith('workbox-precache'))
            .map((name) => caches.delete(name))
        )
      ),
    ])
  );
});

// Precache Vite build assets (JS, CSS, images) — cache only, NO fetch routes.
// Using precache() instead of precacheAndRoute() so Workbox does NOT add its own
// fetch listener. We handle ALL fetches ourselves below to avoid conflicts on iOS.
precache(self.__WB_MANIFEST);

// ============================================================================
// Single fetch handler — handles EVERYTHING (navigation + runtime caching)
// This avoids conflicts between multiple fetch listeners that cause
// double-respondWith errors crashing the SW on iOS Safari.
// ============================================================================

self.addEventListener('fetch', (event) => {
  const { request } = event;
  if (request.method !== 'GET') return;

  const url = new URL(request.url);

  // ── Navigation requests: serve app shell ──
  // Check both request.mode and Accept header (iOS Safari sometimes
  // reports mode as 'same-origin' instead of 'navigate')
  const isNavigation =
    request.mode === 'navigate' ||
    (request.destination === 'document') ||
    (request.headers.get('accept')?.includes('text/html') &&
     !request.headers.get('accept')?.includes('application/json') &&
     url.origin === self.location.origin &&
     !url.pathname.startsWith('/api/'));

  if (isNavigation) {
    event.respondWith(
      fetch(request)
        .then((response) => {
          if (response.ok) {
            const clone = response.clone();
            caches.open(APP_SHELL_CACHE).then((c) => c.put(request, clone));
          }
          return response;
        })
        .catch(() =>
          caches.match(request)
            .then((r) => r || caches.match('/index.html'))
            .then((r) => r || caches.match('/'))
            .then((r) => r || new Response('<h1>Offline</h1>', {
              status: 503,
              headers: { 'Content-Type': 'text/html' },
            }))
        )
    );
    return;
  }

  // ── Precached assets (JS, CSS, SVGs): serve from precache ──
  if (url.origin === self.location.origin &&
      (url.pathname.startsWith('/assets/') ||
       url.pathname.endsWith('.svg') ||
       url.pathname.endsWith('.png') && !url.pathname.startsWith('/storage/'))) {
    event.respondWith(
      caches.match(request, { ignoreSearch: true })
        .then((cached) => cached || fetch(request))
    );
    return;
  }

  // ── Runtime routes below (same logic as before, just inline) ──

  // Google Fonts
  if (url.origin === 'https://fonts.googleapis.com' || url.origin === 'https://fonts.gstatic.com') {
    // Let Workbox handle via registerRoute below
    return;
  }

  // Story metadata
  if (url.pathname.match(/^\/api\/permalink\/[^/]+$/)) {
    // Let Workbox handle via registerRoute below
    return;
  }

  // Story audio
  if (url.pathname.match(/^\/api\/permalink\/[^/]+\/audio$/)) {
    // Let Workbox handle via registerRoute below
    return;
  }

  // Illustration images
  if (url.pathname.startsWith('/storage/stories/') && url.pathname.endsWith('.png')) {
    // Let Workbox handle via registerRoute below
    return;
  }

  // Everything else: just fetch normally (don't call respondWith)
});

// ============================================================================
// Workbox runtime routes (for non-navigation requests only)
// These use Workbox's internal fetch listener, which fires AFTER ours.
// Since we return early (no respondWith) for these URLs above,
// Workbox's listener handles them cleanly.
// ============================================================================

registerRoute(
  ({ url }: { url: URL }) => url.origin === 'https://fonts.googleapis.com',
  new StaleWhileRevalidate({ cacheName: 'google-fonts-stylesheets' })
);

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
  // Evict cached illustrations and metadata after regeneration
  if (event.data?.type === 'EVICT_ILLUSTRATIONS') {
    const { storyId, shortId } = event.data;
    event.waitUntil(Promise.all([
      storyId && caches.open('story-illustrations').then(async (cache) => {
        const keys = await cache.keys();
        const prefix = `/storage/stories/${storyId}/`;
        await Promise.all(
          keys.filter((r) => new URL(r.url).pathname.startsWith(prefix)).map((r) => cache.delete(r))
        );
      }),
      shortId && caches.open('story-metadata').then(async (cache) => {
        const keys = await cache.keys();
        await Promise.all(
          keys.filter((r) => new URL(r.url).pathname.includes(shortId)).map((r) => cache.delete(r))
        );
      }),
    ]));
  }

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
          // Best-effort
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
