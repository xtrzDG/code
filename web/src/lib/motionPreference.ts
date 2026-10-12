/**
 * How much the site moves for this person: as their device asks
 * (`system`: full motion unless the operating system prefers reduced
 * motion) or always calm (`reduce`), whatever the device says. The choice
 * lives in the `aw_motion` cookie, so the server renders
 * <html data-motion="reduce"> and the first paint is already still (the
 * CSS animations of a page start before any script runs).
 *
 * The device's setting always wins over `system`: nobody who asked their
 * operating system for less motion gets more from the cabinet.
 */

export type MotionPreference = "system" | "reduce";

export const DEFAULT_MOTION_PREFERENCE: MotionPreference = "system";

export const MOTION_COOKIE = "aw_motion";

/** The attribute on <html> that calms the page (globals.css, the motion CSS of each part). */
export const MOTION_ATTRIBUTE = "data-motion";

/** The operating system's own setting, as a media query. */
export const REDUCED_MOTION_QUERY = "(prefers-reduced-motion: reduce)";

/** One year: a preference, not a session. */
const MOTION_COOKIE_MAX_AGE_SECONDS = 60 * 60 * 24 * 365;

/** The preference of a cookie value; anything unknown follows the device. */
export function parseMotionPreference(value: string | null | undefined): MotionPreference {
  return value === "reduce" ? "reduce" : DEFAULT_MOTION_PREFERENCE;
}

/** `document.cookie = motionCookie("reduce", secure)`: the choice for a year on the whole site. */
export function motionCookie(preference: MotionPreference, secure: boolean): string {
  return [
    `${MOTION_COOKIE}=${preference}`,
    "path=/",
    `max-age=${MOTION_COOKIE_MAX_AGE_SECONDS}`,
    "samesite=lax",
    ...(secure ? ["secure"] : []),
  ].join("; ");
}

/** The value of <html data-motion> for a preference (none: the device decides). */
export function motionAttribute(preference: MotionPreference): "reduce" | undefined {
  return preference === "reduce" ? "reduce" : undefined;
}

/** Whether things should stay still: the person's choice or the device's setting. */
export function isCalm(preference: MotionPreference, deviceReducesMotion: boolean): boolean {
  return preference === "reduce" || deviceReducesMotion;
}

/**
 * For code outside React's render (an effect deciding whether to count a
 * number up or scroll smoothly): the page's attribute or the device's
 * setting. False on the server.
 */
export function prefersCalmMotion(): boolean {
  if (typeof window === "undefined") {
    return false;
  }
  const isReducedHere = document.documentElement.getAttribute(MOTION_ATTRIBUTE) === "reduce";
  return isCalm(isReducedHere ? "reduce" : "system", window.matchMedia?.(REDUCED_MOTION_QUERY).matches ?? false);
}
