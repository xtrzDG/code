/**
 * How the inbox list is laid out for a person: the row density ("Roomy"
 * shows the avatar and two lines, "Compact" one line per conversation) and,
 * from large screens, the width of the list column the person dragged it
 * to (320–520 px; nothing remembered keeps the responsive default).
 */

export const INBOX_DENSITIES = ["comfortable", "compact"] as const;

export type InboxDensity = (typeof INBOX_DENSITIES)[number];

export const DEFAULT_INBOX_DENSITY: InboxDensity = "comfortable";

/** The names of the remembered choices (lib/userPreference.ts). */
export const DENSITY_PREFERENCE = "inbox-density";
export const LIST_WIDTH_PREFERENCE = "inbox-list-width";

export const MIN_LIST_WIDTH = 320;
export const MAX_LIST_WIDTH = 520;
/** One arrow key press on the column's edge. */
const LIST_WIDTH_STEP = 16;

export function parseDensity(stored: string | null): InboxDensity {
  return stored === "compact" ? "compact" : DEFAULT_INBOX_DENSITY;
}

/** A width within 320–520 px, whole pixels. */
export function clampListWidth(width: number): number {
  return Math.round(Math.min(MAX_LIST_WIDTH, Math.max(MIN_LIST_WIDTH, width)));
}

/** The remembered width, or null for the responsive default (nothing or nonsense stored). */
export function parseListWidth(stored: string | null): number | null {
  if (stored === null || !/^\d{3}$/.test(stored)) {
    return null;
  }
  return clampListWidth(Number(stored));
}

/** The width after a key on the column's edge, or null for another key. */
export function widthAfterKey(key: string, width: number): number | null {
  switch (key) {
    case "ArrowLeft":
      return clampListWidth(width - LIST_WIDTH_STEP);
    case "ArrowRight":
      return clampListWidth(width + LIST_WIDTH_STEP);
    case "Home":
      return MIN_LIST_WIDTH;
    case "End":
      return MAX_LIST_WIDTH;
    default:
      return null;
  }
}

/**
 * The grid columns for a chosen width: the list as chosen, narrowed on a
 * smaller screen so the conversation keeps 440 px, never under 320 px.
 */
export function listColumns(width: number): string {
  return `minmax(${MIN_LIST_WIDTH}px, min(${clampListWidth(width)}px, calc(100% - 460px))) minmax(0, 1fr)`;
}
