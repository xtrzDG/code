/**
 * The review gate: what a person reviewing the screenshots would refuse,
 * checked on every page the visual tests open (shots.ts), before its
 * picture is compared:
 *
 *   - a console error or an uncaught exception while the page loaded
 *     (hydration failures included; nothing is accepted);
 *   - a colour outside the palette (palette.ts): computed text, background,
 *     border, outline, fill and stroke colours of every element shown,
 *     except user content (`data-user-content`), pictures and canvases;
 *   - Cyrillic on an English or Georgian (or Hebrew) page outside user
 *     content (support/consoleClean.ts `strayCyrillic`): an untranslated text;
 *   - a cabinet page taller than four phone screens on a phone (the public
 *     site's reading pages, `isDocument`, may be longer; the pages of
 *     LONG_PHONE_PAGES have their own, larger budget until they are folded).
 */

import type { ConsoleMessage, Page } from "@playwright/test";

import { strayCyrillic } from "../support/consoleClean";
import { renderDeferredBlocks } from "../support/deferredBlocks";
import { expect } from "../support/fixtures";
import { phoneScreensAllowed } from "./heights";
import { ALLOWED_TOKENS, offPalette, type Rgba, type SeenColour } from "./palette";

/** Widths up to this are phones (the gate's height rule). */
const PHONE_MAX_WIDTH = 480;


const consoleErrors = new WeakMap<Page, string[]>();

function describe(message: ConsoleMessage): string {
  const where = message.location().url;
  return `console.${message.type()}: ${message.text()}${where ? ` (${where})` : ""}`;
}

/** Starts recording the page's console errors and uncaught exceptions. */
export function watchConsole(page: Page): void {
  const errors: string[] = [];
  consoleErrors.set(page, errors);
  page.on("console", (message) => {
    if (message.type() === "error") {
      errors.push(describe(message));
    }
  });
  page.on("pageerror", (error) => errors.push(`uncaught: ${error.message}`));
}

/** The errors recorded since the last call. */
function takeConsoleErrors(page: Page): string[] {
  const errors = consoleErrors.get(page) ?? [];
  return errors.splice(0, errors.length);
}

/** Every computed colour of the elements shown, and the allowed tokens' colours, read in the page. */
async function pageColours(page: Page): Promise<{ seen: SeenColour[]; allowed: Rgba[] }> {
  return page.evaluate((tokens) => {
    const canvas = document.createElement("canvas");
    canvas.width = 1;
    canvas.height = 1;
    const context = canvas.getContext("2d", { willReadFrequently: true })!;
    const cache = new Map<string, Rgba | null>();
    // Any CSS colour (rgb, oklab, color-mix…) to sRGB bytes, through the canvas.
    const toRgba = (value: string): Rgba | null => {
      if (!value || value === "none" || value.includes("url(")) {
        return null;
      }
      if (!cache.has(value)) {
        context.clearRect(0, 0, 1, 1);
        context.fillStyle = "rgb(0 0 0 / 0)";
        context.fillStyle = value;
        context.fillRect(0, 0, 1, 1);
        const [red, green, blue, alpha] = context.getImageData(0, 0, 1, 1).data;
        cache.set(value, alpha ? [red!, green!, blue!, alpha / 255] : null);
      }
      return cache.get(value) ?? null;
    };
    const probe = document.createElement("span");
    document.body.append(probe);
    const allowed = tokens.flatMap((token) => {
      probe.style.color = `var(${token})`;
      const colour = toRgba(getComputedStyle(probe).color);
      return colour ? [colour] : [];
    });
    probe.remove();

    const found = new Map<string, SeenColour>();
    const note = (element: Element, property: string, value: string) => {
      const rgba = toRgba(value);
      if (!rgba) {
        return;
      }
      const key = `${rgba.join(",")} ${property}`;
      const entry = found.get(key);
      if (entry) {
        entry.count += 1;
        return;
      }
      const classes = [...element.classList].slice(0, 3).join(".");
      const text = (element.getAttribute("aria-label") ?? element.textContent ?? "").replace(/\s+/g, " ").trim().slice(0, 40);
      const sample = `${element.tagName.toLowerCase()}${classes ? `.${classes}` : ""}${text ? ` "${text}"` : ""}`;
      found.set(key, { rgba, property, count: 1, sample });
    };
    const skipped = "[data-user-content], img, picture, video, canvas, iframe";
    for (const element of document.querySelectorAll("body *")) {
      if (element.closest(skipped) || element.getClientRects().length === 0) {
        continue;
      }
      const style = getComputedStyle(element);
      if (style.visibility === "hidden" || style.opacity === "0") {
        continue;
      }
      const hasText = [...element.childNodes].some((node) => node.nodeType === Node.TEXT_NODE && node.textContent?.trim());
      if (hasText) {
        note(element, "color", style.color);
      }
      note(element, "background-color", style.backgroundColor);
      for (const side of ["Top", "Right", "Bottom", "Left"] as const) {
        if (style[`border${side}Style`] !== "none" && parseFloat(style[`border${side}Width`]) > 0) {
          note(element, "border-color", style[`border${side}Color`]);
        }
      }
      if (style.outlineStyle !== "none" && parseFloat(style.outlineWidth) > 0) {
        note(element, "outline-color", style.outlineColor);
      }
      if (element instanceof SVGElement) {
        note(element, "fill", style.fill);
        note(element, "stroke", style.stroke);
      }
    }
    return { seen: [...found.values()], allowed };
  }, ALLOWED_TOKENS);
}

/** The gate's checks of the page as it is now; each finding fails the test softly, with `label`. */
export async function reviewPage(page: Page, { label, isDocument }: { label: string; isDocument: boolean }): Promise<void> {
  expect.soft(takeConsoleErrors(page), `${label}: console errors`).toEqual([]);
  await renderDeferredBlocks(page);
  const { seen, allowed } = await pageColours(page);
  expect(seen.length, `${label}: the palette scan read the page's colours`).toBeGreaterThan(0);
  expect(allowed, `${label}: the allowed tokens resolved`).toHaveLength(ALLOWED_TOKENS.length);
  expect.soft(offPalette(seen, allowed), `${label}: colours outside the palette`).toEqual([]);
  expect.soft(await strayCyrillic(page), `${label}: interface text in Cyrillic`).toEqual([]);
  const viewport = page.viewportSize();
  if (viewport && viewport.width <= PHONE_MAX_WIDTH && !isDocument) {
    const screens = phoneScreensAllowed(new URL(page.url()).pathname);
    const height = await page.evaluate(() => document.documentElement.scrollHeight);
    expect.soft(height, `${label}: taller than ${screens} phone screens`).toBeLessThanOrEqual(Math.round(screens * viewport.height));
  }
}
