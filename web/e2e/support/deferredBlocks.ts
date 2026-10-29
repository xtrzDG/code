/**
 * The public site's blocks below the first screen are rendered by the
 * browser only near the screen (`.landing-deferred`: content-visibility:
 * auto, src/styles/landing.css). Until then their styles are not resolved,
 * so a check that reads colours (axe, the review gate's palette) renders
 * them first, as a visitor scrolling down would see them.
 */

import type { Page } from "@playwright/test";

export async function renderDeferredBlocks(page: Page): Promise<void> {
  await page.evaluate(() => {
    for (const block of document.querySelectorAll<HTMLElement>(".landing-deferred")) {
      block.style.contentVisibility = "visible";
    }
  });
}
