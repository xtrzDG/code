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
  /** The old page under /b/{businessId}/ ("conversations", "messages/handoffs"). */
  from: string;
  /** Its new place ("inbox"). */
  to: string;
  /** Deeper paths move along (/conversations/{id} -> /inbox/{id}). */
  withSubpaths: boolean;
  /** A query the new place opens with ("view=requests": the inbox on that view). */
  query?: string;
}

/**
 * In the order next.config.ts checks them: a page before the section it is
 * in ("messages/handoffs" before "messages/…"), since the first match wins.
 */
export const LEGACY_ROUTES: readonly LegacyRoute[] = [
  { from: "dashboard", to: "overview", withSubpaths: false },
  // The separate pages of handoffs and requests are views of the team inbox now.
  { from: "messages/handoffs", to: "inbox", withSubpaths: false, query: "view=needs_person" },
  { from: "messages/leads", to: "inbox", withSubpaths: false, query: "view=requests" },
  { from: "handoffs", to: "inbox", withSubpaths: false, query: "view=needs_person" },
  { from: "leads", to: "inbox", withSubpaths: false, query: "view=requests" },
  { from: "messages", to: "inbox", withSubpaths: true },
  { from: "conversations", to: "inbox", withSubpaths: true },
  { from: "knowledge", to: "assistant/knowledge", withSubpaths: true },
  { from: "channels", to: "assistant/channels", withSubpaths: false },
  { from: "billing", to: "settings/billing", withSubpaths: false },
];

export interface NextRedirect {
  source: string;
  destination: string;
  permanent: false;
}

/**
 * The redirects for next.config.ts, and /b/{id} to its overview (before the
 * page streams: before the assistant exists, the business frame shows the
 * setup invitation instead of a page, so a page's own redirect would not run).
 * Next.js keeps the old address's query and adds the route's own.
 */
export function legacyRedirects(): NextRedirect[] {
  return [
    { source: "/b/:businessId", destination: "/b/:businessId/overview", permanent: false },
    ...LEGACY_ROUTES.map(({ from, to, withSubpaths, query }) => ({
      source: `/b/:businessId/${from}${withSubpaths ? "/:rest*" : ""}`,
      destination: `/b/:businessId/${to}${withSubpaths ? "/:rest*" : ""}${query ? `?${query}` : ""}`,
      permanent: false as const,
    })),
  ];
}

/**
 * Where an old path goes now, or null ("/b/x/handoffs" -> "/b/x/inbox?view=needs_person");
 * for tests and links.
 */
export function legacyDestination(pathname: string): string | null {
  const [, root, businessId, ...segments] = pathname.split("/");
  if (root !== "b" || !businessId) {
    return null;
  }
  const rest = segments.join("/");
  if (!rest) {
    return `/b/${businessId}/overview`;
  }
  const route = LEGACY_ROUTES.find(
    (candidate) => rest === candidate.from || (candidate.withSubpaths && rest.startsWith(`${candidate.from}/`)),
  );
  if (!route) {
    return null;
  }
  const deeper = rest.slice(route.from.length);
  return `/b/${businessId}/${route.to}${deeper}${route.query ? `?${route.query}` : ""}`;
}
