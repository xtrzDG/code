/**
 * The cabinet's Content Security Policy, built per page view by the proxy.
 *
 * Scripts run only with the page's nonce (Next.js puts it on its own
 * scripts) or when a trusted script loads them ('strict-dynamic': the
 * route chunks, the Turnstile script of the sign-in page). Styles come
 * from the cabinet's own files or a <style> with the page's nonce: no
 * inline style attribute applies (components set what moves through the
 * CSSOM after hydration, src/lib/csp/clientStyle.ts). Values given to
 * script sinks (innerHTML, script URLs, eval) must pass the page's Trusted
 * Types default policy (src/lib/csp/trustedTypes.ts). The page talks only
 * to its own origin (the BFF at /api/*) and to Cloudflare Turnstile, may
 * not be framed, frames only its own pages (the Channels page's live chat
 * preview) and Turnstile, and forms post only to itself or to the Flitt
 * checkout. Violations are reported to /api/csp-report.
 *
 * `next dev` keeps inline styles and skips Trusted Types: its error overlay
 * injects both. A production build (and the e2e suite on it) enforces them.
 *
 * The pages where an owner signs in with Facebook (lib/metaSignInPages.ts)
 * also let Facebook's JavaScript SDK run (loaded by the connect dialog
 * through the Trusted Types policy `facebook-sdk`, so 'strict-dynamic'
 * admits it; the host is the fallback of older browsers), call Facebook,
 * show its images and frame its sign-in pages.
 */

const TURNSTILE_ORIGIN = "https://challenges.cloudflare.com";
const FLITT_CHECKOUT_ORIGIN = "https://pay.flitt.com";
const FACEBOOK_SDK_ORIGIN = "https://connect.facebook.net";
/** Facebook's pages: its sign-in dialogs and the frames its SDK talks through. */
const FACEBOOK_PAGE_ORIGINS = ["https://www.facebook.com", "https://web.facebook.com", "https://staticxx.facebook.com"];
const FACEBOOK_API_ORIGINS = ["https://www.facebook.com", "https://graph.facebook.com"];
/** Request header with the page's nonce, for Server Components that need it. */
export const NONCE_HEADER = "x-nonce";
const NONCE_BYTES = 16;

/** Where browsers send violation reports (src/app/api/csp-report/route.ts). */
export const CSP_REPORT_PATH = "/api/csp-report";
/** The Reporting API group of the policy (`report-to`). */
const CSP_REPORT_GROUP = "csp";
/** Response header naming the group's endpoint (Reporting API v1). */
export const REPORTING_ENDPOINTS_HEADER = "reporting-endpoints";
export const REPORTING_ENDPOINTS = `${CSP_REPORT_GROUP}="${CSP_REPORT_PATH}"`;

/** A fresh, unpredictable nonce (128 bits, base64). */
export function createNonce(): string {
  const bytes = new Uint8Array(NONCE_BYTES);
  crypto.getRandomValues(bytes);
  return btoa(String.fromCharCode(...bytes));
}

interface PolicyOptions {
  nonce: string;
  /** `next dev`: React rebuilds server error stacks with eval; the overlay injects styles. */
  isDevelopment: boolean;
  /** Served over HTTPS: every request of the page goes over HTTPS too. */
  isHttps: boolean;
  /** A page where the owner signs in with Facebook (lib/metaSignInPages.ts). */
  allowsFacebookSignIn?: boolean;
}

function scriptSource(options: PolicyOptions, extra: readonly string[]): string {
  return [
    "script-src 'self'",
    `'nonce-${options.nonce}'`,
    "'strict-dynamic'",
    ...extra,
    ...(options.isDevelopment ? ["'unsafe-eval'"] : []),
  ].join(" ");
}

/** Styles: the cabinet's files and nonce'd <style> elements only (in development also inline). */
function styleSource(options: PolicyOptions): string {
  return options.isDevelopment ? "style-src 'self' 'unsafe-inline'" : `style-src 'self' 'nonce-${options.nonce}'`;
}

/** What every page adds: Trusted Types (not in development), HTTPS and the reports. */
function closingDirectives(options: PolicyOptions): string[] {
  return [
    ...(options.isDevelopment ? [] : ["require-trusted-types-for 'script'"]),
    ...(options.isHttps ? ["upgrade-insecure-requests"] : []),
    `report-uri ${CSP_REPORT_PATH}`,
    `report-to ${CSP_REPORT_GROUP}`,
  ];
}

export function buildContentSecurityPolicy(options: PolicyOptions): string {
  const facebook = options.allowsFacebookSignIn === true;
  const directives = [
    "default-src 'self'",
    scriptSource(options, [TURNSTILE_ORIGIN, ...(facebook ? [FACEBOOK_SDK_ORIGIN] : [])]),
    styleSource(options),
    ["img-src 'self' data: blob:", ...(facebook ? ["https://www.facebook.com"] : [])].join(" "),
    "font-src 'self' data:",
    "media-src 'self' blob:",
    [`connect-src 'self' ${TURNSTILE_ORIGIN}`, ...(facebook ? FACEBOOK_API_ORIGINS : [])].join(" "),
    [`frame-src 'self' ${TURNSTILE_ORIGIN}`, ...(facebook ? FACEBOOK_PAGE_ORIGINS : [])].join(" "),
    "worker-src 'self' blob:",
    "manifest-src 'self'",
    "object-src 'none'",
    "base-uri 'none'",
    `form-action 'self' ${FLITT_CHECKOUT_ORIGIN}`,
    "frame-ancestors 'none'",
    ...closingDirectives(options),
  ];
  return directives.join("; ");
}

/**
 * The hosted chat page (/c/{address}): stricter than the cabinet's. It
 * runs Next.js and the chat widget (a nonce'd script from the API, styled
 * with constructable stylesheets) and talks only to its own origin and the
 * API (`apiOrigin`, the widget's requests). No Turnstile, no frames, no
 * form posts, never framed, except the cabinet's live preview
 * (`isPreview`, ?preview=1): the Channels page of the same origin frames it.
 */
export function buildHostedChatPolicy(
  options: PolicyOptions & { apiOrigin: string | null; isPreview?: boolean },
): string {
  const directives = [
    "default-src 'self'",
    scriptSource(options, []),
    styleSource(options),
    "img-src 'self' data: blob:",
    "font-src 'self' data:",
    ["connect-src 'self'", ...(options.apiOrigin ? [options.apiOrigin] : [])].join(" "),
    "frame-src 'none'",
    "worker-src 'self'",
    "manifest-src 'self'",
    "object-src 'none'",
    "base-uri 'none'",
    "form-action 'none'",
    options.isPreview ? "frame-ancestors 'self'" : "frame-ancestors 'none'",
    ...closingDirectives(options),
  ];
  return directives.join("; ");
}
