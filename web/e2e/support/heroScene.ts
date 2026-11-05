/**
 * The landing hero's 3D scene in the browser: which device the page
 * thinks it is on, and whether three.js was ever downloaded.
 */

import type { Page } from "@playwright/test";

/**
 * A desktop the scene is meant for (8 cores, 8 GB): headless runners report
 * whatever their virtual machine has, which may be too little for the scene.
 */
export async function emulateCapableDesktop(page: Page): Promise<void> {
  await page.addInitScript(() => {
    Object.defineProperty(Navigator.prototype, "hardwareConcurrency", { get: () => 8, configurable: true });
    Object.defineProperty(Navigator.prototype, "deviceMemory", { get: () => 8, configurable: true });
  });
}

/**
 * Watches every script the page downloads; the returned function tells
 * whether one of them was three.js (its renderer names itself in its
 * messages, so even minified code can be recognised).
 */
export function watchForThreeJs(page: Page): () => Promise<boolean> {
  const verdicts: Promise<boolean>[] = [];
  page.on("response", (response) => {
    if (response.request().resourceType() === "script") {
      verdicts.push(
        response
          .text()
          .then((source) => source.includes("THREE.WebGLRenderer"))
          .catch(() => false),
      );
    }
  });
  return async () => (await Promise.all(verdicts)).some(Boolean);
}

/** The total layout shift (CLS) the page has seen so far. */
export function layoutShift(page: Page): Promise<number> {
  return page.evaluate(
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
}
