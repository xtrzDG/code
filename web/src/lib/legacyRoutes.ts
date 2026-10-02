/**
 * Addresses of the cabinet before its five sections, and where they live
 * now. next.config.ts turns these into redirects (307, so a browser never
 * caches them), which keep the query (?status=new, ?calendar=connected …);
 * bookmarks, links in old messages and the payment page's return keep
 * working. The settings tabs that were in the hash (/settings#team) are
 * moved by the settings page itself: a hash never reaches the server.
 *
 * Self-contained (no "@/" imports): next.config.ts loads it before the app.
 */

export interface LegacyRoute {
  /** The old page under /b/{businessId}/ ("conversations"). */
  from: string;
  /** Its new place ("messages"). */
  to: string;
  /** Deeper paths move along (/conversations/{id} -> /messages/{id}). */
  withSubpaths: boolean;
}

export const LEGACY_ROUTES: readonly LegacyRoute[] = [
  { from: "dashboard", to: "overview", withSubpaths: false },
  { from: "conversations", to: "messages", withSubpaths: true },
  { from: "handoffs", to: "messages/handoffs", withSubpaths: false },
  { from: "leads", to: "messages/leads", withSubpaths: false },
  { from: "knowledge", to: "assistant/knowledge", withSubpaths: true },
  { from: "channels", to: "assistant/channels", withSubpaths: false },
  { from: "billing", to: "settings/billing", withSubpaths: false },
];

export interface NextRedirect {
  source: string;
  destination: string;
  permanent: false;
}

/** The redirects for next.config.ts. */
export function legacyRedirects(): NextRedirect[] {
  return LEGACY_ROUTES.map(({ from, to, withSubpaths }) => ({
    source: `/b/:businessId/${from}${withSubpaths ? "/:rest*" : ""}`,
    destination: `/b/:businessId/${to}${withSubpaths ? "/:rest*" : ""}`,
    permanent: false,
  }));
}

/** Where an old path goes now, or null ("/b/x/handoffs" -> "/b/x/messages/handoffs"); for tests and links. */
export function legacyDestination(pathname: string): string | null {
  const [, root, businessId, page, ...rest] = pathname.split("/");
  if (root !== "b" || !businessId || !page) {
    return null;
  }
  const route = LEGACY_ROUTES.find((candidate) => candidate.from === page);
  if (!route || (rest.length > 0 && !route.withSubpaths)) {
    return null;
  }
  return [`/b/${businessId}/${route.to}`, ...rest].join("/");
}
