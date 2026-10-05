/**
 * The pseudo-locale `en-XA`: English with accented letters, 40 % longer and
 * in brackets, so a layout that breaks on long Russian or Georgian texts
 * breaks on it too, an untranslated (hard-coded) text stands out, and a cut
 * text is easy to spot (its closing bracket is missing).
 *
 * Off by default: a server started with PSEUDO_LOCALE=true serves it to a
 * browser whose language cookie says `en-XA` (web/README.md, "Pseudo-locale").
 */

import type { MessageTree } from "./translate";

const PSEUDO_LOCALE_TAG = "en-xa";

/** How much longer than English a pseudo text is (Russian and Georgian run 20–40 % longer). */
export const PSEUDO_EXPANSION = 0.4;

const LONGEST_FILLER_WORD = 10;

const ACCENTED: Record<string, string> = Object.fromEntries(
  [..."abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"].map((letter, index) => [
    letter,
    [..."áƀçðéƒĝĥíĵķĺɱñóþǫŕšţúṽŵẋýžÁƁÇÐÉƑĜĤÍĴĶĹṀÑÓÞǪŔŠŢÚṼŴẊÝŽ"][index]!,
  ]),
);

const PLACEHOLDER = /(\{\w+\})/;

/** Words of filler: long ones, like Georgian and Russian words, that wrap like real text. */
function filler(length: number): string {
  const words: string[] = [];
  let left = length;
  while (left > 0) {
    const size = Math.min(left, LONGEST_FILLER_WORD);
    words.push("ẋ".repeat(size));
    left -= size + 1;
  }
  return words.join(" ");
}

/** One text in the pseudo-locale; `{placeholders}` stay as they are. */
export function pseudoLocalize(text: string): string {
  const accented = text
    .split(PLACEHOLDER)
    .map((part) => (PLACEHOLDER.test(part) ? part : [...part].map((character) => ACCENTED[character] ?? character).join("")))
    .join("");
  const visibleLength = text.replace(/\{\w+\}/g, "").length;
  const padding = Math.ceil(visibleLength * PSEUDO_EXPANSION);
  return padding > 0 ? `[${accented} ${filler(padding)}]` : `[${accented}]`;
}

/** A whole dictionary (plural forms included) in the pseudo-locale. */
export function pseudoMessages(tree: MessageTree): MessageTree {
  return Object.fromEntries(
    Object.entries(tree).map(([key, value]) => [
      key,
      typeof value === "string" ? pseudoLocalize(value) : value === undefined ? undefined : pseudoMessages(value),
    ]),
  );
}

/** Whether this request gets the pseudo-locale: the server allows it and the cookie asks for it. */
export function wantsPseudoLocale(
  cookieValue: string | null | undefined,
  env: Record<string, string | undefined> = process.env,
): boolean {
  return env.PSEUDO_LOCALE === "true" && cookieValue?.trim().toLowerCase().replace("_", "-") === PSEUDO_LOCALE_TAG;
}
