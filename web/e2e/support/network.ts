/**
 * "The page has settled": no request in flight for a moment. Playwright's
 * `networkidle` never comes on a business page, whose live event stream
 * (GET …/events) stays open for as long as the page does; this waits for
 * every other request of the current document instead. The `test` of
 * fixtures.ts tracks each page from its start, so requests begun before the
 * wait are counted too.
 */

import type { Page, Request } from "@playwright/test";

const EVENT_STREAM = /\/api\/backend\/v1\/businesses\/[^/]+\/events(\?|$)/;
const POLL_INTERVAL_MS = 50;

const inFlight = new WeakMap<Page, Set<Request>>();

/** Starts counting the page's requests (fixtures.ts does it for every test). */
export function trackRequests(page: Page): void {
  const requests = new Set<Request>();
  inFlight.set(page, requests);
  let isLoadingDocument = false;
  page.on("request", (request) => {
    if (request.isNavigationRequest() && request.frame() === page.mainFrame()) {
      isLoadingDocument = true;
    }
    if (!EVENT_STREAM.test(request.url())) {
      requests.add(request);
    }
  });
  page.on("framenavigated", (frame) => {
    if (frame !== page.mainFrame() || !isLoadingDocument) {
      return; // a frame, or the same document (history.pushState)
    }
    // A new document: what the old one had in flight, even what it asked for
    // while the new one loaded, was abandoned with it (and Chromium does not
    // always report those requests as failed).
    isLoadingDocument = false;
    for (const request of requests) {
      if (!request.isNavigationRequest()) {
        requests.delete(request);
      }
    }
  });
  const settle = (request: Request) => requests.delete(request);
  page.on("requestfinished", settle);
  page.on("requestfailed", settle);
}

/** Waits until no request but the live stream has been in flight for `quietMs`. */
export async function waitForNetworkQuiet(page: Page, { quietMs = 500, timeoutMs = 30_000 } = {}): Promise<void> {
  await page.waitForLoadState("load");
  const requests = inFlight.get(page);
  if (!requests) {
    throw new Error("waitForNetworkQuiet: the page is not tracked (use `test` from support/fixtures).");
  }
  const deadline = Date.now() + timeoutMs;
  let quietSince = Date.now();
  while (Date.now() - quietSince < quietMs) {
    if (Date.now() > deadline) {
      const pending = [...requests].map((request) => request.url()).join(", ");
      throw new Error(`The network did not settle within ${timeoutMs} ms: ${pending}`);
    }
    if (requests.size > 0) {
      quietSince = Date.now();
    }
    await new Promise((resolve) => setTimeout(resolve, POLL_INTERVAL_MS));
  }
}
