/**
 * The business's accent on the hosted chat page as a CSS rule for a
 * nonce'd <style> (the Content Security Policy refuses a style attribute):
 * the colour is data, so only a hex colour passes, and nothing else can
 * reach the stylesheet. `main.` outranks the stylesheet's defaults.
 */

const HEX_COLOR = /^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$/;

type AccentProperty = "--hc-accent" | "--hc-on-accent";

/** `selector { --hc-accent: …; … }` with the hex colours given; null when none is one. */
export function accentRule(selector: "main.hc-page" | "main.hc-preview", colors: Partial<Record<AccentProperty, string | null>>): string | null {
  const declarations = Object.entries(colors)
    .filter((entry): entry is [AccentProperty, string] => typeof entry[1] === "string" && HEX_COLOR.test(entry[1]))
    .map(([property, color]) => `${property}:${color.toLowerCase()}`);
  return declarations.length > 0 ? `${selector}{${declarations.join(";")}}` : null;
}
