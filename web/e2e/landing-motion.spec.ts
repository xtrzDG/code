import { expect, test } from "./support/fixtures";
import { en } from "./support/messages";

/**
 * The landing hero: the still picture with reduced motion (the suite's
 * default), the 3D scene without it. The scene itself is drawn by WebGL
 * (SwiftShader on machines without a GPU); the tests check which one is on
 * the page, not its pixels.
 */
test.describe("the landing hero", () => {
  test("shows the still picture and no canvas with reduced motion", async ({ page }) => {
    await page.goto("/");
    const hero = page.getByRole("img", { name: en.landing.hero.sceneLabel });
    await expect(hero).toBeVisible();
    await expect(hero).toHaveAttribute("data-scene", "static");
    // The 3D chunk is never requested: nothing replaces the picture later.
    await page.waitForLoadState("networkidle");
    await expect(page.locator("canvas")).toHaveCount(0);
    await expect(hero).toHaveAttribute("data-scene", "static");
  });

  test.describe("without reduced motion", () => {
    test.use({ contextOptions: { reducedMotion: "no-preference" } });

    test("draws the 3D scene in place of the picture without shifting the page", async ({ page }) => {
      await page.goto("/");
      const hero = page.getByRole("img", { name: en.landing.hero.sceneLabel });
      // Loaded when the page is idle, shown after its first frame.
      await expect(hero).toHaveAttribute("data-scene", "3d", { timeout: 30_000 });
      await expect(hero.locator("canvas")).toHaveCount(1);
      // The scene takes the picture's box: no layout shift (CLS) at all.
      const layoutShift = await page.evaluate(
        () =>
          new Promise<number>((resolve) => {
            let total = 0;
            new PerformanceObserver((list) => {
              for (const entry of list.getEntries() as (PerformanceEntry & { value: number })[]) {
                total += entry.value;
              }
            }).observe({ type: "layout-shift", buffered: true });
            setTimeout(() => resolve(total), 100);
          }),
      );
      expect(layoutShift).toBe(0);
    });

    test("keeps the still picture when the visitor turns reduced motion on", async ({ page }) => {
      await page.goto("/");
      const hero = page.getByRole("img", { name: en.landing.hero.sceneLabel });
      await expect(hero).toHaveAttribute("data-scene", "3d", { timeout: 30_000 });
      await page.emulateMedia({ reducedMotion: "reduce" });
      await expect(hero).toHaveAttribute("data-scene", "static");
      await expect(page.locator("canvas")).toHaveCount(0);
    });
  });

  test("shows every section's content, revealed or not", async ({ page }) => {
    await page.goto("/");
    // Reveals start hidden; scrolling each block into view brings it in.
    for (const id of ["how", "features", "channels", "pricing", "faq"]) {
      const section = page.locator(`#${id}`);
      await section.scrollIntoViewIfNeeded();
      await expect(section.getByRole("heading", { level: 2 })).toBeVisible();
    }
    await expect(page.getByText(en.landing.demo.assistant)).toBeVisible();
  });
});
