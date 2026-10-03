/**
 * The cabinet's Content Security Policy, built per page view by the proxy.
 *
 * Scripts run only with the page's nonce (Next.js puts it on its own
 * scripts) or when a trusted script loads them ('strict-dynamic': the
 * route chunks, the Turnstile script of the sign-in page). Styles stay
 * 'unsafe-inline': React renders style attributes, and a nonce would turn
 * that keyword off. The page talks only to its own origin (the BFF at
 * /api/*) and to Cloudflare Turnstile, may not be framed, and forms post
 * only to itself or to the Flitt checkout.
 */

export const TURNSTILE_ORIGIN = "https://challenges.cloudflare.com";
export const FLITT_CHECKOUT_ORIGIN = "https://pay.flitt.com";
/** Request header with the page's nonce, for Server Components that need it. */
export const NONCE_HEADER = "x-nonce";
const NONCE_BYTES = 16;

/** A fresh, unpredictable nonce (128 bits, base64). */
export function createNonce(): string {
  const bytes = new Uint8Array(NONCE_BYTES);
  crypto.getRandomValues(bytes);
  return btoa(String.fromCharCode(...bytes));
}

export function buildContentSecurityPolicy(options: {
  nonce: string;
  /** `next dev`: React rebuilds server error stacks with eval. */
  isDevelopment: boolean;
  /** Served over HTTPS: every request of the page goes over HTTPS too. */
  isHttps: boolean;
}): string {
  const directives = [
    "default-src 'self'",
    [
      "script-src 'self'",
      `'nonce-${options.nonce}'`,
      "'strict-dynamic'",
      TURNSTILE_ORIGIN,
      ...(options.isDevelopment ? ["'unsafe-eval'"] : []),
    ].join(" "),
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data: blob:",
    "font-src 'self' data:",
    "media-src 'self' blob:",
    `connect-src 'self' ${TURNSTILE_ORIGIN}`,
    `frame-src ${TURNSTILE_ORIGIN}`,
    "worker-src 'self' blob:",
    "manifest-src 'self'",
    "object-src 'none'",
    "base-uri 'none'",
    `form-action 'self' ${FLITT_CHECKOUT_ORIGIN}`,
    "frame-ancestors 'none'",
    ...(options.isHttps ? ["upgrade-insecure-requests"] : []),
  ];
  return directives.join("; ");
}

/**
 * The hosted chat page (/c/{address}): stricter than the cabinet's. It
 * runs Next.js and the chat widget (a nonce'd script from the API) and
 * talks only to its own origin and the API (`apiOrigin`, the widget's
 * requests). No Turnstile, no frames, no form posts, never framed.
 */
export function buildHostedChatPolicy(options: {
  nonce: string;
  apiOrigin: string | null;
  isDevelopment: boolean;
  isHttps: boolean;
}): string {
  const directives = [
    "default-src 'self'",
    [
      "script-src 'self'",
      `'nonce-${options.nonce}'`,
      "'strict-dynamic'",
      ...(options.isDevelopment ? ["'unsafe-eval'"] : []),
    ].join(" "),
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data: blob:",
    "font-src 'self' data:",
    ["connect-src 'self'", ...(options.apiOrigin ? [options.apiOrigin] : [])].join(" "),
    "frame-src 'none'",
    "worker-src 'self'",
    "manifest-src 'self'",
    "object-src 'none'",
    "base-uri 'none'",
    "form-action 'none'",
    "frame-ancestors 'none'",
    ...(options.isHttps ? ["upgrade-insecure-requests"] : []),
  ];
  return directives.join("; ");
}
