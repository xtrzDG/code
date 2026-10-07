/**
 * The cabinet installs as an app: a manifest in the interface language with
 * PNG icons (maskable too), a service worker on signed-in pages, and an
 * offline page kept for when the connection drops.
 */

import { WEB_URL } from "./support/env";
import { expect, test } from "./support/fixtures";
import { en, ru } from "./support/messages";

test.use({ serviceWorkers: "allow" });

interface ManifestIcon {
  src: string;
  sizes: string;
  purpose?: string;
}

test("the manifest names the app in the interface language and its icons load", async ({ page, account }) => {
  expect(account.email).toBeTruthy();
  const manifest = (await (await page.request.get("/manifest.webmanifest")).json()) as Record<string, unknown> & { icons: ManifestIcon[] };
  expect(manifest).toMatchObject({
    name: en.common.appName,
    short_name: en.app.shortName,
    lang: "en",
    start_url: "/businesses",
    scope: "/",
    display: "standalone",
  });
  expect(manifest.icons.map((icon) => `${icon.sizes} ${icon.purpose}`).sort()).toEqual([
    "192x192 any",
    "192x192 maskable",
    "512x512 any",
    "512x512 maskable",
  ]);
  for (const icon of manifest.icons) {
    const response = await page.request.get(icon.src);
    expect(response.headers()["content-type"]).toContain("image/png");
  }

  await page.context().addCookies([{ name: "aw_locale", value: "ru", url: WEB_URL }]);
  const russian = (await (await page.request.get("/manifest.webmanifest")).json()) as { name: string; lang: string };
  expect(russian).toMatchObject({ name: ru.common.appName, lang: "ru" });
});

/*
 * Playwright's offline mode does not reach a service worker's own requests,
 * so what the worker answers without a connection is tested against fakes
 * (src/lib/serviceWorker.test.ts). Here: it registers on a signed-in page,
 * takes it over and keeps the offline page, which renders on its own.
 */
test("the service worker takes over and keeps the offline page", async ({ page, owner }) => {
  await page.goto(`/b/${owner.businessId}/overview`);
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await page.evaluate(async () => {
    await navigator.serviceWorker.ready;
  });
  await page.reload();
  await expect.poll(() => page.evaluate(() => navigator.serviceWorker.controller?.scriptURL ?? null)).toMatch(/\/sw\.js$/);

  const kept = () =>
    page.evaluate(async () => {
      const response = await caches.match("/offline");
      return response ? await response.text() : "";
    });
  await expect.poll(kept).toContain(en.app.offlineTitle);

  await page.goto("/offline");
  await expect(page.getByRole("heading", { level: 1, name: en.app.offlineTitle })).toBeVisible();
  await expect(page.getByText(en.app.offlineDescription)).toBeVisible();
  await page.getByRole("button", { name: en.app.offlineRetry }).click();
  await expect(page).toHaveURL(/\/offline\??$/);
});
