/**
 * The public address of the site (https://app.example.com): canonical
 * links, hreflang alternates, the sitemap and structured data name it.
 * SITE_URL when set (production should set it: a request's Host header is
 * the visitor's to write); else the address the request came in on, as the
 * cabinet's own proxy reports it (local runs, previews).
 */

const FALLBACK_ORIGIN = "http://localhost:3000";

/** The origin of an http(s) address, or null. */
function originOf(value: string | null | undefined): string | null {
  if (!value) {
    return null;
  }
  try {
    const url = new URL(value.trim());
    return url.protocol === "https:" || url.protocol === "http:" ? url.origin : null;
  } catch {
    return null;
  }
}

/** A host name with an optional port, nothing else ("app.example.com:8443"). */
const HOST_PATTERN = /^[A-Za-z0-9.-]+(?::[0-9]{1,5})?$/;

export function siteOrigin(
  requestHeaders: Pick<Headers, "get">,
  env: Record<string, string | undefined> = process.env,
): string {
  const configured = originOf(env.SITE_URL);
  if (configured) {
    return configured;
  }
  const host = (requestHeaders.get("x-forwarded-host") ?? requestHeaders.get("host") ?? "").split(",")[0]?.trim() ?? "";
  if (!HOST_PATTERN.test(host)) {
    return FALLBACK_ORIGIN;
  }
  const forwardedProto = requestHeaders.get("x-forwarded-proto")?.split(",")[0]?.trim();
  const protocol = forwardedProto === "https" || forwardedProto === "http" ? forwardedProto : "http";
  return `${protocol}://${host}`;
}
