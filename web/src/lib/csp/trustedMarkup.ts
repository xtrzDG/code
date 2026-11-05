/**
 * Markup the cabinet builds itself from escaped parts (the printable table
 * card shown in a frame's `srcdoc`), passed to an HTML sink as a Trusted
 * Types value. The page's default policy refuses markup (trustedTypes.ts);
 * this named policy vouches only for what its callers build. Browsers
 * without Trusted Types get the string itself.
 */

interface MarkupPolicy {
  createHTML: (value: string) => unknown;
}

interface TrustedTypesFactory {
  createPolicy: (name: string, rules: { createHTML: (value: string) => string }) => MarkupPolicy;
}

const POLICY_NAME = "cabinet-markup";

let policy: MarkupPolicy | null | undefined;

function markupPolicy(): MarkupPolicy | null {
  if (policy === undefined) {
    const factory = (globalThis as { trustedTypes?: TrustedTypesFactory }).trustedTypes;
    policy = factory ? factory.createPolicy(POLICY_NAME, { createHTML: (value) => value }) : null;
  }
  return policy;
}

/**
 * The markup as the browser's HTML sinks take it. Only for HTML whose
 * every text the caller escaped (buildTableCardHtml, withPoweredByFooter).
 */
export function trustedOwnMarkup(html: string): string {
  const current = markupPolicy();
  // A TrustedHTML object stands in for the string: React passes it to the attribute as it is.
  return current ? (current.createHTML(html) as string) : html;
}
