/**
 * Pure helpers of a resource's calendars (Knowledge → Resources and hours
 * → Calendars) and of Settings → Integrations: the API's shapes, how a
 * source stands, the texts of its problems and of refusals, the check of an
 * iCal address before it is sent, and a resource's one-line summary.
 */

import type { ReasonMessages } from "@/api/errors";
import type { RequestBody, Schema } from "@/api/types";
import type { MessageKey, PluralKey } from "@/i18n/translate";

export type ResourceCalendarView = Schema<"ResourceCalendarView">;
export type BusySourceStatusView = Schema<"BusySourceStatusView">;
export type BookingSystemWriteStatusView = Schema<"BookingSystemWriteStatusView">;
export type CalendarSyncProblem = Schema<"CalendarSyncProblem">;
export type BusyTimeView = Schema<"BusyTimeView">;
export type GoogleCalendarEntry = Schema<"GoogleCalendarEntry">;
export type IntegrationView = Schema<"IntegrationView">;
export type IntegrationKind = Schema<"IntegrationKind">;
export type IntegrationState = Schema<"IntegrationState">;
export type ResourceSyncSummary = Schema<"ResourceSyncSummary">;
export type BookingSystemLinkBody = RequestBody<
  "/v1/businesses/{business_id}/resources/{resource_id}/calendar/booking-system",
  "put"
>;

/** What the owner sees of a problem the last read of a source ran into. */
export const PROBLEM_KEYS: Readonly<Record<CalendarSyncProblem, MessageKey>> = {
  not_connected: "calendarSync.problems.not_connected",
  needs_reconnect: "calendarSync.problems.needs_reconnect",
  not_found: "calendarSync.problems.not_found",
  access_denied: "calendarSync.problems.access_denied",
  address_refused: "calendarSync.problems.address_refused",
  timeout: "calendarSync.problems.timeout",
  unreachable: "calendarSync.problems.unreachable",
  not_a_calendar: "calendarSync.problems.not_a_calendar",
  provider_error: "calendarSync.problems.provider_error",
};

const REFUSAL_CODES = [
  "feed_limit",
  "feed_already_imported",
  "address_refused",
  "calendar_invalid",
  "access_denied",
  "not_found",
  "timeout",
  "unreachable",
  "provider_error",
  "public_address_missing",
] as const;

/** Refusals of calendar changes (422 reason codes) in the owner's language. */
export const CALENDAR_REFUSAL_MESSAGES: ReasonMessages = Object.fromEntries(
  REFUSAL_CODES.map((code) => [code, () => ({ key: `calendarSync.refusals.${code}` as MessageKey })]),
);

export type SourceHealth = "synced" | "problem" | "waiting";

/** How a source stands: its last read failed, it read fine, or it was not read yet. */
export function sourceHealth(status: BusySourceStatusView | null | undefined): SourceHealth {
  if (status?.problem) {
    return "problem";
  }
  return status?.last_synced_at ? "synced" : "waiting";
}

const FEED_SCHEMES = ["https://", "http://", "webcal://"] as const;
const MIN_FEED_LENGTH = 12;
const MAX_FEED_LENGTH = 2048;

/** What is wrong with a typed iCal address before it is sent (null: send it). */
export function feedAddressError(raw: string): MessageKey | null {
  const address = raw.trim();
  if (!address) {
    return "calendarSync.ical.required";
  }
  const lower = address.toLowerCase();
  const scheme = FEED_SCHEMES.find((prefix) => lower.startsWith(prefix));
  const rest = scheme ? address.slice(scheme.length) : "";
  if (!scheme || !rest || /\s/.test(address) || address.length < MIN_FEED_LENGTH || address.length > MAX_FEED_LENGTH) {
    return "calendarSync.ical.invalid";
  }
  return null;
}

const EVENT_TYPE_PATTERN = /^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$/;

/** What is wrong with a booking system's form (each field's message key). */
export function bookingSystemErrors(eventType: string, apiKey: string): { eventType?: MessageKey; apiKey?: MessageKey } {
  const errors: { eventType?: MessageKey; apiKey?: MessageKey } = {};
  const id = eventType.trim();
  if (!id) {
    errors.eventType = "calendarSync.bookingSystem.eventTypeRequired";
  } else if (!EVENT_TYPE_PATTERN.test(id)) {
    errors.eventType = "calendarSync.bookingSystem.eventTypeInvalid";
  }
  if (!apiKey.trim()) {
    errors.apiKey = "calendarSync.bookingSystem.apiKeyRequired";
  }
  return errors;
}

/** The sources that block a resource (its Google calendar, imported feeds, booking system). */
export function sourceCount(view: ResourceCalendarView): number {
  return (view.google.status ? 1 : 0) + view.ical_imports.length + (view.booking_system ? 1 : 0);
}

export type SummaryLine =
  | { key: PluralKey; count: number; tone: "neutral" | "warning" }
  | { key: MessageKey; count?: undefined; tone: "neutral" };

/** The resource row's line about its calendars; null when it has none. */
export function summaryLine(summary: ResourceSyncSummary | undefined): SummaryLine | null {
  if (!summary) {
    return null;
  }
  if (summary.problem_count > 0) {
    return { key: "calendarSync.row.problems", count: summary.problem_count, tone: "warning" };
  }
  if (summary.source_count > 0) {
    return { key: "calendarSync.row.sources", count: summary.source_count, tone: "neutral" };
  }
  return summary.is_export_on ? { key: "calendarSync.row.shared", tone: "neutral" } : null;
}

/** Badge tones of an integration's state. */
export const STATE_TONES: Readonly<Record<IntegrationState, "neutral" | "success" | "warning">> = {
  off: "neutral",
  on: "success",
  attention: "warning",
  unavailable: "neutral",
};

interface RangeFormat {
  date: (value: number) => string;
  dateTime: (value: number) => string;
  time: (value: number) => string;
}

/** A busy time as one line: the end's date only when it ends on another day. */
export function busyRange(block: Pick<BusyTimeView, "starts_at" | "ends_at">, format: RangeFormat): string {
  const end = format.date(block.starts_at) === format.date(block.ends_at) ? format.time(block.ends_at) : format.dateTime(block.ends_at);
  return `${format.dateTime(block.starts_at)} – ${end}`;
}

/** The value a choice of the Google list sends: the account's own calendar is "primary". */
export function googleChoiceValue(entry: GoogleCalendarEntry): string {
  return entry.is_primary ? "primary" : entry.calendar_id;
}

/** The account's calendars with its own calendar first, then by name. */
export function sortGoogleCalendars(entries: readonly GoogleCalendarEntry[], locale: string): GoogleCalendarEntry[] {
  return [...entries].sort(
    (a, b) => Number(Boolean(b.is_primary)) - Number(Boolean(a.is_primary)) || a.name.localeCompare(b.name, locale),
  );
}

/** The linked calendar's entry in the account's list ("primary" is the account's own). */
export function linkedGoogleEntry(calendarId: string, entries: readonly GoogleCalendarEntry[]): GoogleCalendarEntry | undefined {
  return entries.find((entry) => googleChoiceValue(entry) === calendarId || entry.calendar_id === calendarId);
}
