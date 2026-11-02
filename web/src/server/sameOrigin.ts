/**
 * The BFF's guard against cross-site request forgery (on top of the
 * SameSite=Lax session cookie):
 *  - a write (POST, PUT, PATCH, DELETE) must come from the cabinet's own
 *    pages: `Sec-Fetch-Site: same-origin`, or, from a browser that does not
 *    send it, an Origin equal to the site's (SITE_URL, or the address the
 *    request came in on, which another site's page cannot change). A write
 *    with neither header is refused, and so is any other Sec-Fetch-Site (a
 *    sibling subdomain is `same-site`);
 *  - a read is let through, except an audited export (a CSV, a business's
 *    archive, a customer's data): a link or a fetch from another site
 *    (`cross-site`, `same-site`, or another Origin) would make the owner's
 *    browser download it and write the audit entry in the owner's name.
 *    An address typed or opened from a bookmark (`none`) still works.
 * The widget, the hosted chat and the booking page's API calls do not pass
 * here (they go to the API itself, or are the cabinet's own fetches).
 */

import { siteOrigin } from "./siteOrigin";

type Env = Record<string, string | undefined>;

/** A host name with an optional port, nothing else ("app.example.com:8443"). */
const HOST_PATTERN = /^[A-Za-z0-9.-]+(?::[0-9]{1,5})?$/;

/**
 * The origin the request came in on, as the cabinet's own proxy reports it
 * (X-Forwarded-Host and -Proto, else Host): a page of another site cannot
 * make the visitor's browser send another Host, so an Origin equal to it is
 * the site's own. Null for a host that is not a plain host name.
 */
function requestOrigin(headers: Headers): string | null {
  const host = (headers.get("x-forwarded-host") ?? headers.get("host") ?? "").split(",")[0]?.trim().toLowerCase() ?? "";
  if (!HOST_PATTERN.test(host)) {
    return null;
  }
  const forwardedProto = headers.get("x-forwarded-proto")?.split(",")[0]?.trim();
  const protocol = forwardedProto === "https" || forwardedProto === "http" ? forwardedProto : "http";
  return `${protocol}://${host}`;
}

const SAFE_METHODS: ReadonlySet<string> = new Set(["GET", "HEAD", "OPTIONS"]);

/** API paths whose GET downloads data and writes an audit entry. */
const AUDITED_EXPORTS: readonly RegExp[] = [
  /^\/v1\/businesses\/[^/]+\/exports\/[^/]+$/,
  /^\/v1\/business-exports\/[^/]+\/[^/]+\/download$/,
  /^\/v1\/businesses\/[^/]+\/contacts\/[^/]+\/export$/,
  /^\/v1\/businesses\/[^/]+\/customer-segments\/[^/]+\/export$/,
];

export function isAuditedExportPath(backendPath: string): boolean {
  return AUDITED_EXPORTS.some((pattern) => pattern.test(backendPath));
}

/** The Origin header names the site itself. */
function isOwnOrigin(origin: string, headers: Headers, env: Env): boolean {
  return origin === siteOrigin(headers, env) || origin === requestOrigin(headers);
}

/** The request comes from one of the site's own pages. */
export function isSameOriginRequest(headers: Headers, env: Env = process.env): boolean {
  const fetchSite = headers.get("sec-fetch-site");
  if (fetchSite !== null) {
    return fetchSite === "same-origin";
  }
  const origin = headers.get("origin");
  return origin !== null && isOwnOrigin(origin, headers, env);
}

/** A read another site started: a cross-site or same-site fetch or navigation, or another Origin. */
function isForeignRead(headers: Headers, env: Env): boolean {
  const fetchSite = headers.get("sec-fetch-site");
  if (fetchSite === "cross-site" || fetchSite === "same-site") {
    return true;
  }
  const origin = headers.get("origin");
  return origin !== null && !isOwnOrigin(origin, headers, env);
}

/**
 * True when the BFF refuses the request (403 `forbidden_origin`): a write
 * not from the site's own pages, or an audited export (`backendPath`)
 * another site asked for.
 */
export function isCrossSiteRequest(
  method: string,
  headers: Headers,
  backendPath: string | null = null,
  env: Env = process.env,
): boolean {
  if (!SAFE_METHODS.has(method.toUpperCase())) {
    return !isSameOriginRequest(headers, env);
  }
  return backendPath !== null && isAuditedExportPath(backendPath) && isForeignRead(headers, env);
}
