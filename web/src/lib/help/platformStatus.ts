/**
 * The public status page and the cabinet's announcement banner, as plain
 * functions: the colour of each level, the share of good days in a
 * component's 90-day history, and which announcements the banner shows.
 */

import type { Schema } from "@/api/types";
import type { BadgeTone } from "@/components/ui/Badge";

export type PlatformStatus = Schema<"PlatformStatusView">;
export type StatusLevel = Schema<"StatusLevel">;
export type StatusComponent = Schema<"StatusComponent">;
export type StatusDay = Schema<"StatusDayView">;
export type Announcement = Schema<"AnnouncementView">;
export type AnnouncementLevel = Schema<"AnnouncementLevel">;

export const STATUS_COMPONENTS: readonly StatusComponent[] = ["chat", "meta", "telegram", "voice", "cabinet"];
export const ANNOUNCEMENT_LEVELS: readonly AnnouncementLevel[] = ["info", "maintenance", "degraded", "outage"];

/** How often an open page looks again (the API measures every five minutes). */
export const STATUS_POLL_MS = 60_000;

export const LEVEL_TONES: Readonly<Record<StatusLevel, BadgeTone>> = {
  operational: "success",
  maintenance: "info",
  degraded: "warning",
  outage: "danger",
  no_data: "neutral",
};

export const ANNOUNCEMENT_TONES: Readonly<Record<AnnouncementLevel, BadgeTone>> = {
  info: "info",
  maintenance: "info",
  degraded: "warning",
  outage: "danger",
};

/** The bar colour of a day (design tokens). */
export const DAY_COLOURS: Readonly<Record<StatusLevel, string>> = {
  operational: "bg-success",
  maintenance: "bg-info",
  degraded: "bg-warning",
  outage: "bg-danger",
  no_data: "bg-line-strong",
};

/** The share (0 to 1) of measured days without a slowdown or an outage; null before any day is measured. */
export function goodDayShare(history: readonly StatusDay[]): number | null {
  const measured = history.filter((day) => day.level !== "no_data");
  if (measured.length === 0) {
    return null;
  }
  const good = measured.filter((day) => day.level === "operational" || day.level === "maintenance");
  return good.length / measured.length;
}

/** An outage must stay in sight: its banner cannot be hidden. */
export function canDismiss(announcement: Pick<Announcement, "level">): boolean {
  return announcement.level !== "outage";
}

/**
 * The announcements the banner shows: in effect or planned, minus those
 * the person hid (an outage always shows), the most serious first.
 */
export function bannerAnnouncements(status: PlatformStatus | undefined, dismissed: readonly string[]): Announcement[] {
  if (!status) {
    return [];
  }
  const rank = (level: AnnouncementLevel) => ANNOUNCEMENT_LEVELS.indexOf(level);
  return status.announcements
    .filter((announcement) => !canDismiss(announcement) || !dismissed.includes(dismissKey(announcement)))
    .sort((left, right) => rank(right.level) - rank(left.level) || right.updated_at - left.updated_at);
}

/** The key of a hidden banner: a changed announcement (new text or level) shows again. */
export function dismissKey(announcement: Pick<Announcement, "id" | "updated_at">): string {
  return `${announcement.id}@${announcement.updated_at}`;
}

/** The hidden banners kept in the browser, as a list of keys (anything else reads as none). */
export function parseDismissed(raw: string | null): string[] {
  if (!raw) {
    return [];
  }
  try {
    const value: unknown = JSON.parse(raw);
    return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string").slice(-20) : [];
  } catch {
    return [];
  }
}
