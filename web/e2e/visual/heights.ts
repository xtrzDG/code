/**
 * The review gate's height rule (gate.ts): on a phone (390×844) a cabinet
 * page takes at most four screens, so the front desk finds things without
 * scrolling through a wall; the public site's reading pages are exempt.
 */

const MAX_PHONE_SCREENS = 4;

/**
 * Pages already longer than four phone screens when the gate came, with
 * the screens each may take at most (its tallest language, rounded up to
 * a quarter screen). A ratchet: lower a budget when its page gets shorter,
 * drop the entry once the page fits in four screens, never raise one or add
 * a page (fold the page instead, as the Overview folds its statistics).
 * Their length is the business's own lists (knowledge, invoices, review
 * requests), a long settings form, the platform admin's dashboards, or
 * Georgian's longer words (the Overview: four screens in Russian and
 * English since its invitation folds, 14 px more in Georgian).
 */
const LONG_PHONE_PAGES: readonly (readonly [RegExp, number])[] = [
  [/\/assistant\/knowledge$/, 7],
  [/\/settings\/billing$/, 6.5],
  [/\/settings\/reviews$/, 5.75],
  [/\/overview\/reports$/, 5],
  [/\/b\/[^/]+\/settings$/, 4.75],
  [/\/assistant\/channels$/, 4.25],
  [/\/b\/[^/]+\/overview$/, 4.25],
  [/^\/admin\/system$/, 7],
  [/^\/admin\/metrics$/, 7.5],
  [/^\/admin\/clients\/[^/]+$/, 8.25],
];

/** The phone screens a page may take: four, or its budget in LONG_PHONE_PAGES. */
export function phoneScreensAllowed(pathname: string): number {
  return LONG_PHONE_PAGES.find(([page]) => page.test(pathname))?.[1] ?? MAX_PHONE_SCREENS;
}
