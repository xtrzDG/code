/**
 * Rules of the bookings list: grouping by day, what staff may do with a
 * booking, nights of a stay, the customer's language and the reminder.
 */

import { daysBetween, type LocalDateText } from "@/components/insights/dates";
import type { BookingStatus, BookingView } from "@/components/insights/types";

export interface BookingDay {
  date: LocalDateText;
  bookings: BookingView[];
}

/** Bookings by local day; days and times ascending (newest day first for past ranges). */
export function groupBookingsByDate(bookings: readonly BookingView[], options: { newestFirst?: boolean } = {}): BookingDay[] {
  const sorted = [...bookings].sort(
    (left, right) => left.date.localeCompare(right.date) || (left.time ?? "").localeCompare(right.time ?? ""),
  );
  const days: BookingDay[] = [];
  for (const booking of sorted) {
    const last = days.at(-1);
    if (last && last.date === booking.date) {
      last.bookings.push(booking);
    } else {
      days.push({ date: booking.date, bookings: [booking] });
    }
  }
  return options.newestFirst ? days.reverse() : days;
}

export interface BookingActions {
  confirm: boolean;
  complete: boolean;
  noShow: boolean;
  reschedule: boolean;
  cancel: boolean;
}

/**
 * What staff may do with a booking (backend UpdateBookingUseCase:
 * completed, no-show and cancelled from pending or confirmed; confirm from
 * pending). Finished bookings are read-only.
 */
export function bookingActions(status: BookingStatus): BookingActions {
  const active = status === "pending" || status === "confirmed";
  return {
    confirm: status === "pending",
    complete: active,
    noShow: active,
    reschedule: active,
    cancel: active,
  };
}

/** Nights of a stay (0 for a time slot ending the same day). */
export function nightsOf(booking: Pick<BookingView, "date" | "end_date">): number {
  return Math.max(0, daysBetween(booking.date, booking.end_date));
}

/** The customer's language for texts about a booking: theirs when the business speaks it. */
export function customerLanguage(
  booking: Pick<BookingView, "language">,
  business: { languages: readonly string[]; default_language: string },
): string {
  return booking.language && business.languages.includes(booking.language) ? booking.language : business.default_language;
}

export type ReminderState = "sent" | "pending" | "none";

/**
 * The customer's reminder: sent (when), still to come for an upcoming
 * active booking, or none (finished, cancelled or already started).
 */
export function reminderState(
  booking: Pick<BookingView, "reminder_sent_at" | "status" | "date">,
  today: LocalDateText,
): ReminderState {
  if (booking.reminder_sent_at) {
    return "sent";
  }
  const isActive = booking.status === "pending" || booking.status === "confirmed";
  return isActive && booking.date >= today ? "pending" : "none";
}
