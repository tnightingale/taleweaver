import { test, expect } from '@playwright/test';
import { readFileSync } from 'fs';
import path from 'path';

/**
 * Offline authentication tests.
 *
 * Verify that authenticated users can access cached content offline
 * without being redirected to the login page.
 *
 * Requires the production app to be running (docker compose up app)
 * with a seeded test user (handled by global-setup.ts).
 */

const AUTH_FILE = path.join(__dirname, '..', '.test-auth.json');

function getTestCredentials() {
  try {
    return JSON.parse(readFileSync(AUTH_FILE, 'utf-8'));
  } catch {
    return null;
  }
}

async function login(page: import('@playwright/test').Page) {
  const creds = getTestCredentials();
  if (!creds) {
    test.skip(true, 'No test credentials — global setup may not have run');
    return;
  }

  // Log in via the UI
  await page.goto('/login');
  await page.fill('input[type="email"]', creds.email);
  await page.fill('input[type="password"]', creds.password);
  await page.click('button[type="submit"]');

  // Wait for redirect to home (auth completed)
  await page.waitForURL('/', { timeout: 10_000 });
}

test.describe('Offline auth', () => {
  test('does not redirect to login when offline after authentication', async ({ page, context }) => {
    await login(page);

    // Verify we're authenticated (should see "Sign out" or user content)
    await expect(page.locator('text=Taleweaver')).toBeVisible();

    // Let SW cache everything
    await page.waitForTimeout(3000);

    // Go offline
    await context.setOffline(true);

    // Refresh — should NOT redirect to /login
    await page.reload({ timeout: 15_000 });

    // Should still see app content, not login page
    const url = page.url();
    expect(url).not.toContain('/login');
    await expect(page.locator('text=Taleweaver')).toBeVisible({ timeout: 10_000 });

    await context.setOffline(false);
  });

  test('auth resolves within 5 seconds when offline', async ({ page, context }) => {
    await login(page);
    await page.waitForTimeout(3000); // Let SW cache

    await context.setOffline(true);

    const start = Date.now();
    await page.reload({ timeout: 15_000 });

    // Wait for the app to render (auth spinner should resolve)
    await expect(page.locator('text=Taleweaver')).toBeVisible({ timeout: 10_000 });

    const elapsed = Date.now() - start;
    console.log(`Auth resolved in ${elapsed}ms`);

    // Should resolve within 5 seconds (3s timeout + margin)
    expect(elapsed).toBeLessThan(5000);

    await context.setOffline(false);
  });
});

test.describe('HTTP cache headers', () => {
  test('HTML responses have max-age for offline fallback', async ({ request }) => {
    const response = await request.get('/');
    const cacheControl = response.headers()['cache-control'];
    console.log('Cache-Control for /:', cacheControl);

    expect(cacheControl).toContain('max-age=');
    // Should have a max-age > 0 (for Safari tab offline fallback)
    const maxAge = parseInt(cacheControl.match(/max-age=(\d+)/)?.[1] || '0');
    expect(maxAge).toBeGreaterThan(0);
  });

  test('hashed assets have immutable cache headers', async ({ request }) => {
    // Fetch the HTML to find an asset URL
    const htmlResponse = await request.get('/');
    const html = await htmlResponse.text();

    // Extract a hashed JS asset from the HTML
    const assetMatch = html.match(/src="(\/assets\/[^"]+\.js)"/);
    if (!assetMatch) {
      test.skip(true, 'No hashed asset found in HTML');
      return;
    }

    const assetResponse = await request.get(assetMatch[1]);
    const cacheControl = assetResponse.headers()['cache-control'];
    console.log(`Cache-Control for ${assetMatch[1]}:`, cacheControl);

    expect(cacheControl).toContain('immutable');
    expect(cacheControl).toContain('max-age=31536000');
  });

  test('Google Fonts CSS loads asynchronously (non-render-blocking)', async ({ request }) => {
    const response = await request.get('/');
    const html = await response.text();

    // Should NOT have a render-blocking Google Fonts link
    expect(html).not.toMatch(
      /<link[^>]+href="https:\/\/fonts\.googleapis\.com[^>]+rel="stylesheet"[^>]*>/
    );

    // Should have the async-loading pattern (media="print" onload)
    expect(html).toContain('media="print"');
    expect(html).toContain('onload=');
  });
});

test.describe('Offline SW navigation', () => {
  test('SW serves cached app shell when offline', async ({ page, context }) => {
    // Visit to register SW and cache app shell
    await page.goto('/');
    await page.waitForTimeout(3000);

    // Verify SW is active
    const swActive = await page.evaluate(async () => {
      const reg = await navigator.serviceWorker.getRegistration('/');
      return !!reg?.active;
    });
    expect(swActive).toBe(true);

    // Go offline and reload
    await context.setOffline(true);
    await page.reload({ timeout: 15_000 });

    // Should see the app (not browser error page)
    await expect(page.locator('text=Taleweaver')).toBeVisible({ timeout: 10_000 });

    // Should have dark background (inline critical CSS working)
    const bgColor = await page.evaluate(() => {
      return getComputedStyle(document.body).backgroundColor;
    });
    // #0a0a1a in rgb
    expect(bgColor).not.toBe('rgb(255, 255, 255)'); // not white

    await context.setOffline(false);
  });

  test('user identity is cached in localStorage for offline use', async ({ page }) => {
    await login(page);

    // Check localStorage has the cached user
    const cachedUser = await page.evaluate(() => {
      const raw = localStorage.getItem('tw-user');
      return raw ? JSON.parse(raw) : null;
    });

    expect(cachedUser).not.toBeNull();
    expect(cachedUser).toHaveProperty('email');
    expect(cachedUser).toHaveProperty('id');
  });
});
