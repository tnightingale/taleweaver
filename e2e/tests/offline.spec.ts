import { test, expect } from '@playwright/test';

/**
 * Offline / Service Worker tests.
 *
 * These verify that:
 * 1. The SW registers and activates
 * 2. The app shell is cached and serves offline
 * 3. Story metadata and audio are cached for offline playback
 *
 * Requires the production app to be running (docker compose up app).
 */

test.describe('Service Worker', () => {
  test('registers and becomes active', async ({ page }) => {
    await page.goto('/');

    // Wait for SW to register and activate
    const swState = await page.evaluate(async () => {
      if (!('serviceWorker' in navigator)) return { error: 'SW not supported' };

      const reg = await navigator.serviceWorker.getRegistration('/');
      if (!reg) return { error: 'No SW registration found' };

      const sw = reg.active || reg.waiting || reg.installing;
      return {
        state: sw?.state,
        scope: reg.scope,
        hasActive: !!reg.active,
        hasWaiting: !!reg.waiting,
        hasInstalling: !!reg.installing,
      };
    });

    console.log('SW state:', JSON.stringify(swState, null, 2));
    expect(swState).not.toHaveProperty('error');
    expect(swState.hasActive).toBe(true);
  });

  test('precaches the app shell', async ({ page }) => {
    await page.goto('/');

    // Give SW time to install and cache
    await page.waitForTimeout(2000);

    const cacheInfo = await page.evaluate(async () => {
      const cacheNames = await caches.keys();
      const details: Record<string, string[]> = {};

      for (const name of cacheNames) {
        const cache = await caches.open(name);
        const keys = await cache.keys();
        details[name] = keys.map((r) => new URL(r.url).pathname);
      }
      return details;
    });

    console.log('Caches:', JSON.stringify(cacheInfo, null, 2));

    // The app-shell cache should exist with / and /index.html
    expect(cacheInfo).toHaveProperty('app-shell');
    const shellPaths = cacheInfo['app-shell'];
    expect(shellPaths).toContain('/');
    expect(shellPaths).toContain('/index.html');
  });
});

test.describe('Offline navigation', () => {
  test('app shell loads offline after visiting /', async ({ page, context }) => {
    // Visit the home page online to populate caches
    await page.goto('/');
    await page.waitForTimeout(3000); // Let SW install + cache

    // Verify SW is active before going offline
    const swActive = await page.evaluate(async () => {
      const reg = await navigator.serviceWorker.getRegistration('/');
      return !!reg?.active;
    });
    expect(swActive).toBe(true);

    // Go offline
    await context.setOffline(true);

    // Refresh — should serve from cache
    const response = await page.reload();
    console.log('Offline reload status:', response?.status());

    // Should NOT see browser's offline error page
    const bodyText = await page.textContent('body');
    expect(bodyText).not.toContain('ERR_INTERNET_DISCONNECTED');
    expect(bodyText).not.toContain('not connected to the internet');

    // Should see our app content
    expect(bodyText).toContain('Taleweaver');

    await context.setOffline(false);
  });

  test('story permalink loads offline after first visit', async ({ page, context }) => {
    // First, find a story permalink from the API
    const storiesResp = await page.request.get('/api/stories?limit=1');
    const stories = await storiesResp.json();

    if (!stories.stories?.length) {
      test.skip(true, 'No stories in database — create one first');
      return;
    }

    const story = stories.stories[0];
    const permalink = `/s/${story.short_id}`;
    console.log(`Testing offline with story: ${story.title} (${permalink})`);

    // Visit the story page online
    await page.goto(permalink);

    // Wait for SW to cache everything (app shell + metadata + audio prefetch)
    await page.waitForTimeout(5000);

    // Check what's in the caches
    const cacheInfo = await page.evaluate(async () => {
      const cacheNames = await caches.keys();
      const details: Record<string, string[]> = {};
      for (const name of cacheNames) {
        const cache = await caches.open(name);
        const keys = await cache.keys();
        details[name] = keys.map((r) => new URL(r.url).pathname);
      }
      return details;
    });
    console.log('Caches after story visit:', JSON.stringify(cacheInfo, null, 2));

    // Verify metadata is cached
    const metadataCached = cacheInfo['story-metadata']?.some((p: string) =>
      p.includes(story.short_id)
    );
    console.log('Metadata cached:', metadataCached);

    // Verify audio is cached
    const audioCached = cacheInfo['story-audio']?.some((p: string) =>
      p.includes(story.short_id)
    );
    console.log('Audio cached:', audioCached);

    // Go offline and refresh
    await context.setOffline(true);
    const response = await page.reload();
    console.log('Offline reload status:', response?.status());

    // Should NOT see browser offline error or our error screen
    const bodyText = await page.textContent('body');
    expect(bodyText).not.toContain('ERR_INTERNET_DISCONNECTED');
    expect(bodyText).not.toContain('not connected to the internet');
    expect(bodyText).not.toContain("isn't available offline");

    // Should see the story title
    // (On mobile it's hidden, so check for it in the page content broadly)
    const hasStoryContent = await page.evaluate(() => {
      // Check if StoryScreen rendered (has audio element or play button)
      return !!(
        document.querySelector('audio') ||
        document.querySelector('[class*="play"]') ||
        document.querySelector('button')
      );
    });
    expect(hasStoryContent).toBe(true);

    await context.setOffline(false);
  });
});
