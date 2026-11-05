/**
 * Time and screens of the visual tests: the same moment on every run, so a
 * screenshot taken today matches the one taken a year ago.
 *
 * The API's wall clock starts at VISUAL_CLOCK_START (scripts/visual_api.py,
 * started by playwright.config.ts in a visual run): the demo businesses
 * (SEED_DEMO_DATA) are seeded relative to it, a Wednesday late morning in
 * Tbilisi, far from midnight and from a change of summer time. The browser's
 * clock stands still at VISUAL_VIEW_TIME, a minute and a half later: "12 min
 * ago" reads the same however long the run takes.
 */

/** The API's wall clock at its first reading: Wednesday 14 October 2026, 11:30 in Tbilisi. */
export const VISUAL_CLOCK_START = "2026-10-14T07:30:00+00:00";

/** The browser's clock on every page (page.clock.setFixedTime). */
export const VISUAL_VIEW_TIME = new Date(Date.parse(VISUAL_CLOCK_START) + 90_000);

/** The demo restaurant's zone, the browser's too. */
export const VISUAL_ZONE = "Asia/Tbilisi";

/** The large screen: 1440×900, one device pixel per CSS pixel. */
export const DESKTOP = { viewport: { width: 1440, height: 900 }, isMobile: false, hasTouch: false } as const;

/** The phone of the suite's phone tests (phone-loop.spec.ts): 390×844, touch. */
export const PHONE = { viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true } as const;

export type Screen = typeof DESKTOP | typeof PHONE;
