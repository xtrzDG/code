/**
 * Platform support's access to a cabinet as the banner shows it: whether
 * anyone from support is there, and the choices of how long the owner lets
 * them make changes (the API takes 1 to 168 hours, a day by default).
 */

import type { SupportAccessView } from "@/api/types";

export const WRITE_ACCESS_HOURS = [2, 8, 24, 72, 168] as const;
export const DEFAULT_WRITE_ACCESS_HOURS = 24;

/** How often an open cabinet asks whether support came or left. */
export const SUPPORT_ACCESS_POLL_MS = 60_000;

/** The banner shows while support looks in or may make changes. */
export function isSupportPresent(view: SupportAccessView | undefined): boolean {
  return Boolean(view && ((view.sessions ?? []).length > 0 || view.write_access?.is_allowed));
}

/** When the last open look ends (the banner's "until"), or null. */
export function supportUntil(view: SupportAccessView): number | null {
  const ends = (view.sessions ?? []).map((session) => session.expires_at);
  return ends.length > 0 ? Math.max(...ends) : null;
}
