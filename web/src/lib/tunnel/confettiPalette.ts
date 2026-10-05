/**
 * The colours of the go-live confetti: clay, sand and ink only (the
 * cabinet's accent and its quiet companion, and the page's own text
 * colour), so the celebration stays inside the palette in both themes.
 */

/** Clay (the accent, both schemes) and sand (the accent's companion, both schemes). */
export const CONFETTI_CLAY_SAND = ["#ad5732", "#e19a75", "#c48d4e", "#d9a86c", "#e8d6bf"] as const;

/** Ink when the page's text colour cannot be read (the dark theme's ink). */
export const FALLBACK_INK = "#ecebe6";

/** The confetti palette with the page's ink: `rgb(…)` or `#rrggbb` from getComputedStyle. */
export function confettiPalette(ink: string | null | undefined): readonly string[] {
  const color = ink?.trim();
  return [...CONFETTI_CLAY_SAND, color && /^(#[0-9a-f]{3,8}|rgba?\([\d.,\s/%]+\))$/i.test(color) ? color : FALLBACK_INK];
}
