/**
 * Pure rules of Bookings → Waitlist: the three lists (still waiting,
 * booked, ended) and their counts, how an entry's wish reads (the day,
 * the hours, the party), the place held for it and the minutes left to
 * answer, and the hold choices of the settings.
 */

import type { Schema } from "@/api/types";
import type { BadgeTone } from "@/components/ui";
import type { MessageKey } from "@/i18n/translate";

export type WaitlistEntry = Schema<"WaitlistEntryView">;
export type WaitlistStatus = Schema<"WaitlistStatus">;
export type WaitlistEndReason = Schema<"WaitlistEndReason">;
export type WaitlistSettings = Schema<"WaitlistSettingsView">;
export type WaitlistPage = Schema<"WaitlistEntryPage">;

/** The lists of the page, as the API filters them (`?filter=`). */
export const WAITLIST_FILTERS = ["active", "booked", "ended"] as const;
export type WaitlistFilter = (typeof WAITLIST_FILTERS)[number];

export function isWaitlistFilter(value: string | null | undefined): value is WaitlistFilter {
  return value !== null && value !== undefined && (WAITLIST_FILTERS as readonly string[]).includes(value);
}

/** The statuses each list holds. */
const FILTER_STATUSES: Record<WaitlistFilter, readonly WaitlistStatus[]> = {
  active: ["waiting", "offered"],
  booked: ["booked"],
  ended: ["expired"],
};

/** How many entries each list holds, from the counts by status. */
export function filterCounts(counts: readonly Schema<"WaitlistStatusCount">[]): Record<WaitlistFilter, number> {
  const of = (filter: WaitlistFilter) =>
    counts.filter((count) => FILTER_STATUSES[filter].includes(count.status)).reduce((total, count) => total + count.count, 0);
  return { active: of("active"), booked: of("booked"), ended: of("ended") };
}

export const STATUS_LABELS: Record<WaitlistStatus, MessageKey> = {
  waiting: "waitlist.status.waiting",
  offered: "waitlist.status.offered",
  booked: "waitlist.status.booked",
  expired: "waitlist.status.expired",
};

export const STATUS_TONES: Record<WaitlistStatus, BadgeTone> = {
  waiting: "neutral",
  offered: "accent",
  booked: "success",
  expired: "neutral",
};

export const END_REASON_LABELS: Record<WaitlistEndReason, MessageKey> = {
  declined: "waitlist.endReasons.declined",
  no_answer: "waitlist.endReasons.no_answer",
  date_passed: "waitlist.endReasons.date_passed",
  unreachable: "waitlist.endReasons.unreachable",
  removed: "waitlist.endReasons.removed",
};

export const EMPTY_TEXTS: Record<WaitlistFilter, { title: MessageKey; description: MessageKey }> = {
  active: { title: "waitlist.empty.active", description: "waitlist.empty.activeDescription" },
  booked: { title: "waitlist.empty.booked", description: "waitlist.empty.bookedDescription" },
  ended: { title: "waitlist.empty.ended", description: "waitlist.empty.endedDescription" },
};

/** The hours a customer would take: any, between two times, from or until one. */
export type WishedWindow =
  | { kind: "any" }
  | { kind: "between"; from: string; to: string }
  | { kind: "from"; from: string }
  | { kind: "until"; to: string };

export function wishedWindow(entry: Pick<WaitlistEntry, "time_from" | "time_to">): WishedWindow {
  const from = entry.time_from ?? null;
  const to = entry.time_to ?? null;
  if (from && to) {
    return { kind: "between", from, to };
  }
  if (from) {
    return { kind: "from", from };
  }
  return to ? { kind: "until", to } : { kind: "any" };
}

/** Whether staff may take the entry off the list (it still waits, or a place is held for it). */
export function isRemovable(entry: Pick<WaitlistEntry, "status">): boolean {
  return entry.status === "waiting" || entry.status === "offered";
}

/**
 * Whole minutes left to answer a held place (rounded up, so "1 minute left"
 * until it is gone), 0 once the hold is over, null without a hold.
 */
export function minutesLeft(expiresAtMicros: number | null | undefined, nowMs: number): number | null {
  if (expiresAtMicros === null || expiresAtMicros === undefined) {
    return null;
  }
  const leftMs = expiresAtMicros / 1000 - nowMs;
  return leftMs <= 0 ? 0 : Math.ceil(leftMs / 60_000);
}

/** How long a freed place may be held (the API takes 15 to 120 minutes). */
export const HOLD_MINUTES = [15, 20, 30, 45, 60, 90, 120] as const;

/** The hold choices, the stored one among them even if it is not a usual step. */
export function holdOptions(current: number): readonly number[] {
  return HOLD_MINUTES.includes(current as (typeof HOLD_MINUTES)[number])
    ? HOLD_MINUTES
    : [...HOLD_MINUTES, current].sort((left, right) => left - right);
}
