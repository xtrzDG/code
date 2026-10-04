/**
 * The front desk's "Today" on a phone: today's arrivals by time, which of
 * them can be marked (arrived or no-show) because their start has come,
 * where "now" falls among them, and the day's tally. Cancelled bookings
 * leave the agenda and are only counted.
 */

import type { BookingView } from "@/components/insights/types";

import { hasStarted } from "./bookingList";

export interface AgendaEntry {
  booking: BookingView;
  /** Pending or confirmed: still to be marked. */
  isActive: boolean;
  /** Active and started: "Arrived" and "No-show" are allowed. */
  canMark: boolean;
}

export interface AgendaCounts {
  /** Still to come or to be marked. */
  toCome: number;
  arrived: number;
  missed: number;
  cancelled: number;
}

export interface TodayAgenda {
  entries: AgendaEntry[];
  /**
   * Where the "now" line goes: before this entry (the first that starts
   * later); null when every entry is ahead or every one has started.
   */
  nowIndex: number | null;
  counts: AgendaCounts;
}

function startOf(booking: Pick<BookingView, "time">): string {
  return booking.time?.slice(0, 5) ?? "00:00";
}

/** Today's bookings as the agenda shows them (`localNow`: "YYYY-MM-DDTHH:MM" in the business's zone). */
export function todayAgenda(bookings: readonly BookingView[], localNow: string): TodayAgenda {
  const counts: AgendaCounts = { toCome: 0, arrived: 0, missed: 0, cancelled: 0 };
  const entries: AgendaEntry[] = [];
  for (const booking of bookings) {
    if (booking.status === "cancelled") {
      counts.cancelled += 1;
      continue;
    }
    const isActive = booking.status === "pending" || booking.status === "confirmed";
    if (isActive) {
      counts.toCome += 1;
    } else if (booking.status === "completed") {
      counts.arrived += 1;
    } else {
      counts.missed += 1;
    }
    entries.push({ booking, isActive, canMark: isActive && hasStarted(booking, localNow) });
  }
  entries.sort(
    (left, right) =>
      left.booking.date.localeCompare(right.booking.date) ||
      startOf(left.booking).localeCompare(startOf(right.booking)) ||
      (left.booking.contact_name ?? "").localeCompare(right.booking.contact_name ?? ""),
  );
  const firstAhead = entries.findIndex((entry) => !hasStarted(entry.booking, localNow));
  const nowIndex = firstAhead > 0 ? firstAhead : null;
  return { entries, nowIndex, counts };
}

/** "20:00" of a local "YYYY-MM-DDTHH:MM" moment. */
export function timeOfMoment(localMoment: string): string {
  return localMoment.slice(11, 16);
}
