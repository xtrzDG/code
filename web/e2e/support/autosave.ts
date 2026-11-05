/**
 * Settings forms that save themselves (components/forms/useAutosaveForm):
 * there is no Save button, so a test waits for the save itself, then for
 * the line over the form to say the latest changes are saved.
 */

import type { Locator, Page, Response } from "@playwright/test";

/**
 * The next successful save (PUT or PATCH) to an API path ending in `path`:
 * start waiting before the change that makes it.
 */
export function nextSave(page: Page, path: string): Promise<Response> {
  return page.waitForResponse((response) => {
    const method = response.request().method();
    return (method === "PUT" || method === "PATCH") && new URL(response.url()).pathname.endsWith(path) && response.ok();
  });
}

/** "Saved" over a form that saves itself (`saved` is the text in the page's language). */
export function savedHint(scope: Page | Locator, saved: string): Locator {
  return scope.locator('[data-autosave-state="saved"]').filter({ hasText: saved });
}

/** A field's own "Saved" beside its label. */
export function savedPill(scope: Page | Locator, saved: string): Locator {
  return scope.locator('[data-save-status="saved"]').filter({ hasText: saved });
}
