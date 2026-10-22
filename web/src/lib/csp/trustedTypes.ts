/**
 * The page's Trusted Types default policy (the policy requires them for
 * every script sink: `require-trusted-types-for 'script'`). It runs as a
 * nonce'd script in <head> (TrustedTypesScript), before Next.js's runtime
 * loads any chunk, so every sink a library reaches passes it:
 *
 *  - HTML: only text, which cannot make an element (no "<": a JSON-LD
 *    block, text React writes), and the `<script></script>` React parses
 *    to create a script element it never runs;
 *  - script URLs: the page's own origin (route chunks, the service
 *    worker, blob: workers) and the listed origins (Cloudflare Turnstile);
 *  - script text and eval: only a JSON object or array, which cannot call
 *    anything.
 *
 * Anything else is refused: the sink throws and the browser reports the
 * violation (/api/csp-report). The function runs as an inline script, so
 * it uses nothing from outside its own body.
 */

interface TrustedTypePolicyOptions {
  createHTML: (value: string) => string | null;
  createScript: (value: string) => string | null;
  createScriptURL: (value: string) => string | null;
}

/** What the policy needs of `window` (a fake one in tests). */
export interface TrustedTypesWindow {
  trustedTypes?: {
    defaultPolicy?: unknown;
    createPolicy: (name: string, options: TrustedTypePolicyOptions) => unknown;
  };
  location: { origin: string };
  document: { baseURI: string };
}

export function installTrustedTypesPolicy(win: TrustedTypesWindow, scriptOrigins: readonly string[]): void {
  const factory = win.trustedTypes;
  if (!factory || typeof factory.createPolicy !== "function" || factory.defaultPolicy) {
    return;
  }
  const pageOrigin = win.location.origin;
  factory.createPolicy("default", {
    createHTML: function (value) {
      return value === "<script></script>" || value.indexOf("<") === -1 ? value : null;
    },
    createScript: function (value) {
      const text = value.trim();
      if (text.charAt(0) !== "{" && text.charAt(0) !== "[") {
        return null;
      }
      try {
        JSON.parse(text);
        return value;
      } catch {
        return null;
      }
    },
    // The address stays as it was written: React and Next.js's chunk loader find a
    // script already on the page by its src attribute, so "/_next/…" must not become absolute.
    createScriptURL: function (value) {
      try {
        const url = new URL(value, win.document.baseURI);
        return url.origin === pageOrigin || scriptOrigins.indexOf(url.origin) !== -1 ? value : null;
      } catch {
        return null;
      }
    },
  });
}

/** Origins whose scripts the cabinet loads besides its own. */
export const TRUSTED_SCRIPT_ORIGINS: readonly string[] = ["https://challenges.cloudflare.com"];

/**
 * The inline script that installs the policy as the page starts. "</" is
 * written "<\/" (the same string in JavaScript), so no text in it can
 * close the <script> element.
 */
export function trustedTypesBootstrap(): string {
  const source = `(${installTrustedTypesPolicy.toString()})(window, ${JSON.stringify(TRUSTED_SCRIPT_ORIGINS)});`;
  return source.replace(/<\//g, "<\\/");
}
