/**
 * The console-clean gate of every spec (fixtures.ts): a test fails when a
 * page of its browser context
 *
 *   - throws (`pageerror`), or logs a `console.error` the test did not
 *     accept with `consoleErrors.allow(/…/)`;
 *   - reports a hydration failure, React's #418 (text) or #423 (the tree),
 *     as an error or a warning: never acceptable, `allow` cannot hide it.
 *
 * And, with `cyrillicCheck` (on by default; E2E_CYRILLIC_CHECK=0 or
 * `test.use({ cyrillicCheck: false })` turns it off), an English or
 * Georgian page whose interface shows Cyrillic text at the end of a test
 * fails too: an untranslated text of the cabinet. User content is left
 * out: anything marked `data-user-content` (the cabinet marks names,
 * messages, knowledge, notes and the like, `UserContent`/`UserSentence`
 * in the UI kit), form fields, code and text marked with another `lang`.
 */

import type { BrowserContext, ConsoleMessage, Page } from "@playwright/test";

/** React's production hydration errors and their development wording. */
export const HYDRATION_ERROR =
  /Minified React error #(418|423)\b|Hydration failed|hydration (error|mismatch)|did not match\. Server|server rendered (HTML|text) didn't match/i;

export interface ConsoleRecord {
  /** Errors a test may accept (an expected 4xx, say). */
  errors: string[];
  /** Hydration failures: never accepted. */
  hydration: string[];
}

function describe(message: ConsoleMessage): string {
  const where = message.location().url;
  return `console.${message.type()}: ${message.text()}${where ? ` (${where})` : ""}`;
}

/** Records what one page logs and throws into `record`. */
export function watchPage(page: Page, record: ConsoleRecord): void {
  page.on("console", (message) => {
    const text = describe(message);
    if (HYDRATION_ERROR.test(message.text())) {
      record.hydration.push(text);
    } else if (message.type() === "error") {
      record.errors.push(text);
    }
  });
  page.on("pageerror", (error) => {
    const text = `uncaught: ${error.message}`;
    (HYDRATION_ERROR.test(error.message) ? record.hydration : record.errors).push(text);
  });
}

/** Watches the context's pages now and later (popups, `context.newPage()`). */
export function watchContext(context: BrowserContext, record: ConsoleRecord): void {
  for (const page of context.pages()) {
    watchPage(page, record);
  }
  context.on("page", (page) => watchPage(page, record));
}

/** The errors no `allow` pattern accepts. */
export function unexpectedErrors(record: ConsoleRecord, allowed: readonly RegExp[]): string[] {
  return [...record.hydration, ...record.errors.filter((error) => !allowed.some((pattern) => pattern.test(error)))];
}

/**
 * Interface text in Cyrillic on an English or Georgian page (empty on a
 * Russian page): visible text nodes outside user content.
 */
export async function strayCyrillic(page: Page): Promise<string[]> {
  if (page.isClosed()) {
    return [];
  }
  return page.evaluate(() => {
    const pageLanguage = (document.documentElement.lang || "en").slice(0, 2);
    if (pageLanguage === "ru") {
      return [];
    }
    const userContent = "[data-user-content], input, textarea, select, option, [contenteditable], script, style, noscript, code, pre";
    const found = new Set<string>();
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    while (walker.nextNode()) {
      const node = walker.currentNode;
      const text = (node.textContent ?? "").replace(/\s+/g, " ").trim();
      const element = node.parentElement;
      if (!text || !element || !/[Ѐ-ӿ]/.test(text) || element.closest(userContent)) {
        continue;
      }
      // Text the page marks as another language (a language's own name, a customer's message).
      const marked = element.closest("[lang]")?.getAttribute("lang")?.slice(0, 2);
      if (marked && marked !== pageLanguage) {
        continue;
      }
      const style = getComputedStyle(element);
      if (style.visibility === "hidden" || style.display === "none" || element.getClientRects().length === 0) {
        continue;
      }
      found.add(text.slice(0, 80));
    }
    return [...found];
  });
}
