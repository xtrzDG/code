/**
 * The time zone of the person reading a page that belongs to no business
 * (Account → Security, the status page, the platform admin). Business pages
 * use the business zone (`useBusinessFormat()`).
 *
 * The browser's zone is kept in the `aw_tz` cookie, so the server renders
 * the same times the browser shows and hydration never mismatches. Until the
 * cookie exists (the very first page), times are shown in UTC with the
 * label "UTC", and the browser switches to its own zone right after
 * hydration.
 */

import { isKnownTimeZone } from "./intl/calendarFields";

export const VIEWER_TIME_ZONE_COOKIE = "aw_tz";

/** One year: the zone is a property of the device, refreshed on every visit. */
const VIEWER_TIME_ZONE_MAX_AGE_SECONDS = 60 * 60 * 24 * 365;

/** The zone shown before the viewer's own is known. */
export const FALLBACK_TIME_ZONE = "UTC";

/** A cookie value as a zone Intl knows, or null. */
export function parseViewerTimeZone(value: string | null | undefined): string | null {
  if (!value) {
    return null;
  }
  let zone: string;
  try {
    zone = decodeURIComponent(value);
  } catch {
    return null;
  }
  return /^[A-Za-z0-9_+\-/]+$/.test(zone) && isKnownTimeZone(zone) ? zone : null;
}

/** `document.cookie` assignment that remembers the device's zone on the whole site. */
export function viewerTimeZoneCookie(zone: string, secure: boolean): string {
  return [
    `${VIEWER_TIME_ZONE_COOKIE}=${encodeURIComponent(zone)}`,
    "path=/",
    `max-age=${VIEWER_TIME_ZONE_MAX_AGE_SECONDS}`,
    "samesite=lax",
    ...(secure ? ["secure"] : []),
  ].join("; ");
}
