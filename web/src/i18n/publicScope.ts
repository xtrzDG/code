/**
 * The public site's share of the dictionary. A public page (/en, /ru/for/
 * hotel, /ka/terms: the proxy marks them with the path's language) renders
 * its texts on the server; only its client components (the theme and
 * language switches, the demo chat, the value calculator, the country
 * picker, the toasts…) read the dictionary in the browser. So the root
 * layout hands them these sections alone rather than the whole cabinet's,
 * which would otherwise travel inside every page (about 280 KB of text).
 *
 * The texts are the ones the client modules reachable from the public
 * pages name: publicScope.test.ts walks those imports and fails when this
 * list misses one or keeps one nobody reads. Leaving the public site for a
 * cabinet page loads that page in full (I18nProvider), so the cabinet
 * always gets its whole dictionary.
 */

import type { MessageTree } from "./translate";

/**
 * Whole sections ("landing") or single texts ("knowledge.form.priceAmbiguous")
 * the public site's client components read.
 */
export const PUBLIC_CLIENT_TEXTS: readonly string[] = [
  "chrome",
  "common",
  "errors",
  "formFields",
  "knowledge.form.priceAmbiguous",
  "knowledge.form.priceTooPrecise",
  "landing.pricing.country",
  "landing.pricing.show",
  "language",
  "mfa.errors",
  "mfa.secondStep",
  "mfa.stepUp",
  "publicDemo",
  "roi",
  "shell",
  "theme",
  "validation",
];

/** Which part of the dictionary a page's client components get. */
export type TextScope = "full" | "public";

/** The texts of `messages` the public site's client components read (PUBLIC_CLIENT_TEXTS), in the same shape. */
export function publicClientMessages(messages: MessageTree): MessageTree {
  const picked: MessageTree = {};
  for (const entry of PUBLIC_CLIENT_TEXTS) {
    const segments = entry.split(".");
    let source: MessageTree | string | undefined = messages;
    for (const segment of segments) {
      source = typeof source === "object" ? source[segment] : undefined;
    }
    if (source === undefined) {
      continue;
    }
    let target = picked;
    for (const segment of segments.slice(0, -1)) {
      const next = target[segment];
      target = typeof next === "object" ? next : (target[segment] = {});
    }
    target[segments.at(-1) ?? ""] = source;
  }
  return picked;
}
