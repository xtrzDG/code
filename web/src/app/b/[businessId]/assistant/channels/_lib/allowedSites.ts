/**
 * The websites allowed to show the business's website chat, as the owner
 * types them. The API stores each one as its origin (scheme, host and
 * port); the cabinet reads an address the same way first, so a typo is
 * caught before saving and one site is listed once.
 */

/** As many sites as the API keeps. */
export const MAX_ALLOWED_SITES = 20;

const DEFAULT_PORTS: Record<string, string> = { "http:": "80", "https:": "443" };

/**
 * "cafe-batumi.ge/menu" -> "https://cafe-batumi.ge"; "http://Shop.ge:8080"
 * -> "http://shop.ge:8080". Null when the text is not a website address
 * (no dot in the host, another scheme, spaces).
 */
export function siteOrigin(text: string): string | null {
  const raw = text.trim();
  if (raw === "" || /\s/.test(raw)) {
    return null;
  }

  const withScheme = raw.includes("://") ? raw : `https://${raw}`;
  let url: URL;
  try {
    url = new URL(withScheme);
  } catch {
    return null;
  }

  if (!(url.protocol in DEFAULT_PORTS)) {
    return null;
  }

  const host = url.hostname.toLowerCase().replace(/\.$/, "");
  if (host === "" || (!host.includes(".") && host !== "localhost")) {
    return null;
  }

  const port = url.port === "" || url.port === DEFAULT_PORTS[url.protocol] ? "" : `:${url.port}`;
  return `${url.protocol}//${host}${port}`;
}

/** What two origins share as one site: the host without "www." and the port. */
export function siteKey(origin: string): string {
  try {
    const url = new URL(origin);
    return `${url.hostname.replace(/^www\./, "")}:${url.port}`;
  } catch {
    return origin;
  }
}

/** Whether `origin` names a site already on the list. */
export function hasSite(sites: readonly string[], origin: string): boolean {
  const key = siteKey(origin);
  return sites.some((site) => siteKey(site) === key);
}

/** The origin without its scheme, as an owner recognizes it: "cafe-batumi.ge". */
export function siteLabel(origin: string): string {
  return origin.replace(/^https?:\/\//, "");
}

/** Whether two lists hold the same sites in the same order. */
export function isSameSiteList(left: readonly string[], right: readonly string[]): boolean {
  return left.length === right.length && left.every((site, index) => site === right[index]);
}
