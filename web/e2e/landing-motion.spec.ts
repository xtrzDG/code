import type { Page } from "@playwright/test";

import { expect, test } from "./support/fixtures";
import { emulateCapableDesktop, layoutShift, watchForThreeJs } from "./support/heroScene";
import { en } from "./support/messages";

/**
 * The landing hero: a poster drawn by HTML and CSS comes with the page (the
 * first thing the visitor sees), and only a capable wide screen without
 * reduced motion or data saving swaps in the 3D scene later, whose code
 * (three.js) no other page and no other device downloads. The scene is
 * drawn by WebGL (SwiftShader without a GPU); the tests check which one is
 * on the page and what was downloaded, not pixels.
 */

const heroOf = (page: Page) => page.getByRole("img", { name: en.landing.hero.sceneLabel });

test.describe("the landing hero", () => {
  test("is the poster with reduced motion, and three.js is never fetched", async ({ page }) => {
    const loadedThree = watchForThreeJs(page);
    await page.goto("/");
    const hero = heroOf(page);
    await expect(hero).toHaveAttribute("data-scene-reason", "reduced-motion");
    await page.waitForLoadState("networkidle");
    await expect(hero).toHaveAttribute("data-scene", "static");
    await expect(page.locator("canvas")).toHaveCount(0);
    expect(await loadedThree()).toBe(false);
  });

  test.describe("on a capable wide screen without reduced motion", () => {
    test.use({ contextOptions: { reducedMotion: "no-preference" } });

    test.beforeEach(async ({ page }) => {
      await emulateCapableDesktop(page);
    });

    test("comes as a poster, then the 3D scene fades in over it without shifting the page", async ({ page }) => {
      const loadedThree = watchForThreeJs(page);
      const response = await page.goto("/");
      // The server sends the poster: the largest paint never waits for WebGL.
      expect(await response?.text()).toContain('data-scene="static"');
      const hero = heroOf(page);
      // Loaded once the page has loaded and the browser is idle, shown after its first frame.
      await expect(hero).toHaveAttribute("data-scene", "3d", { timeout: 30_000 });
      await expect(hero.locator("canvas")).toHaveCount(1);
      expect(await layoutShift(page)).toBe(0);
      expect(await loadedThree()).toBe(true);
    });

    test("goes back to the poster when the visitor turns reduced motion on", async ({ page }) => {
      await page.goto("/");
      const hero = heroOf(page);
      await expect(hero).toHaveAttribute("data-scene", "3d", { timeout: 30_000 });
      await page.emulateMedia({ reducedMotion: "reduce" });
      await expect(hero).toHaveAttribute("data-scene-reason", "reduced-motion");
      await expect(page.locator("canvas")).toHaveCount(0);
    });

    test("keeps the poster when the browser asks to save data", async ({ page }) => {
      await page.addInitScript(() => {
        Object.defineProperty(Navigator.prototype, "connection", { get: () => ({ saveData: true }), configurable: true });
      });
      const loadedThree = watchForThreeJs(page);
      await page.goto("/");
      await expect(heroOf(page)).toHaveAttribute("data-scene-reason", "save-data");
      await page.waitForLoadState("networkidle");
      expect(await loadedThree()).toBe(false);
    });
  });

  test.describe("on a phone", () => {
    test.use({
      viewport: { width: 390, height: 844 },
      isMobile: true,
      hasTouch: true,
      contextOptions: { reducedMotion: "no-preference" },
    });

    test("is the moving CSS poster, and three.js is never fetched", async ({ page }) => {
      // Even a strong phone: the narrow screen decides.
      await emulateCapableDesktop(page);
      const loadedThree = watchForThreeJs(page);
      await page.goto("/");
      const hero = heroOf(page);
      await expect(hero).toHaveAttribute("data-scene-reason", "narrow-screen");
      // The poster moves by itself: its rings turn in 3D.
      await expect(hero.locator(".hero-still-ring").first()).toHaveCSS("animation-name", "aw-orbit-turn");
      await page.waitForLoadState("networkidle");
      await expect(page.locator("canvas")).toHaveCount(0);
      expect(await loadedThree()).toBe(false);
      expect(await layoutShift(page)).toBe(0);
    });
  });

  test("brings every section's content in as it is scrolled to", async ({ page }) => {
    await page.goto("/");
    for (const id of ["how", "features", "channels", "pricing", "faq"]) {
      const section = page.locator(`#${id}`);
      await section.scrollIntoViewIfNeeded();
      // A reveal starts transparent; seen once, it is marked and shown for good.
      const reveal = section.locator("[data-reveal]").first();
      await expect(reveal).toHaveAttribute("data-revealed", "");
      await expect(reveal).toHaveCSS("opacity", "1");
      await expect(section.getByRole("heading", { level: 2 })).toBeVisible();
    }
    await expect(page.getByText(en.landing.demo.assistant)).toBeVisible();
  });
});

test.describe("pages without the 3D hero", () => {
  test.use({ contextOptions: { reducedMotion: "no-preference" } });

  for (const path of ["/ru/for/restaurant", "/en/terms", "/login"]) {
    test(`never download three.js: ${path}`, async ({ page }) => {
      await emulateCapableDesktop(page);
      const loadedThree = watchForThreeJs(page);
      await page.goto(path);
      await page.waitForLoadState("networkidle");
      expect(await loadedThree()).toBe(false);
    });
  }
});
