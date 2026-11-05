/**
 * Rules of the bookings list: grouping by day, what staff may do with a
 * booking, nights of a stay, the customer's language and the reminder.
 */

import { daysBetween, type LocalDateText } from "@/components/insights/dates";
import type { BookingStatus, BookingView } from "@/components/insights/types";
import { calendarParts } from "@/lib/intl/calendarFields";

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

export type BookingActionKey = keyof BookingActions;

/**
 * What staff may do with a booking (backend UpdateBookingUseCase:
 * completed, no-show and cancelled from pending or confirmed; confirm from
 * pending). "Completed" and "no-show" wait for the start time: before it
 * nobody can have come or stayed away. Finished bookings are read-only.
 */
export function bookingActions(status: BookingStatus, hasStarted = true): BookingActions {
  const active = status === "pending" || status === "confirmed";
  return {
    confirm: status === "pending",
    complete: active && hasStarted,
    noShow: active && hasStarted,
    reschedule: active,
    cancel: active,
  };
}

export interface BookingActionLayout {
  /** The one main button: confirm a request, else mark it completed once it started, else edit. */
  primary: BookingActionKey | "edit";
  /** The rest, under "More", the destructive cancel last. */
  more: (BookingActionKey | "edit")[];
}

const MORE_ORDER: readonly (BookingActionKey | "edit")[] = ["complete", "noShow", "reschedule", "edit", "cancel"];

export function bookingActionLayout(actions: BookingActions): BookingActionLayout {
  const primary = actions.confirm ? "confirm" : actions.complete ? "complete" : "edit";
  const more = MORE_ORDER.filter((key) => key !== primary && (key === "edit" || actions[key]));
  return { primary, more };
}

/** "YYYY-MM-DDTHH:MM" now in a time zone, to compare with a booking's local start. */
export function localNowIn(timeZone: string, now: Date = new Date()): string {
  const parts = calendarParts(
    now,
    timeZone,
    { year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", hourCycle: "h23" },
    "en-CA",
  );
  return `${parts.year}-${parts.month}-${parts.day}T${parts.hour}:${parts.minute}`;
}

/** Whether a booking's start (its date, and time when it has one) has come, in the business's local time. */
export function hasStarted(booking: Pick<BookingView, "date" | "time">, localNow: string): boolean {
  return `${booking.date}T${booking.time?.slice(0, 5) ?? "00:00"}` <= localNow;
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

/** What a booking is worth, formatted in its currency ("€35"); null without a value. */
export function bookingValueText(
  booking: Pick<BookingView, "value_minor" | "currency_code">,
  money: (minor: number, currency?: string) => string,
): string | null {
  if (booking.value_minor === null || booking.value_minor === undefined) {
    return null;
  }
  return money(booking.value_minor, booking.currency_code ?? undefined);
}
