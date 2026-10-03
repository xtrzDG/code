/**
 * Pure helpers of bookable resources and of holidays / special-hours days
 * (Knowledge -> "Resources and hours").
 *
 * Dates of schedule exceptions are business-local "YYYY-MM-DD" and hours
 * are minutes of that local day (closing may be 1440 = midnight).
 */

import type { OpeningInterval, RequestBody, ResourceKind, Schema, Weekday } from "@/api/types";
import type { MessageKey } from "@/i18n/translate";

import { formatMinutesOfDay, parseTimeOfDay } from "./format";
import { dateTimeFormat } from "./intl/formatters";

export type ResourceView = Schema<"ResourceView">;
export type BookingUnit = Schema<"BookingUnit">;
export type ScheduleExceptionView = Schema<"ScheduleExceptionView">;
export type ResourceCreateBody = RequestBody<"/v1/businesses/{business_id}/resources", "post">;
export type ResourcePatchBody = RequestBody<"/v1/businesses/{business_id}/resources/{resource_id}", "patch">;
export type ScheduleExceptionCreateBody = RequestBody<"/v1/businesses/{business_id}/schedule-exceptions", "post">;

export const RESOURCE_KINDS: readonly ResourceKind[] = ["table", "room", "staff", "arena", "bay", "vehicle", "slot"];
export const BOOKING_UNITS: readonly BookingUnit[] = ["time_slot", "night"];

export const MAX_CAPACITY = 10_000;
export const MAX_UNITS = 1000;
export const MIN_SLOT_MINUTES = 5;
export const MAX_SLOT_MINUTES = 43_200;

// --- Resources -------------------------------------------------------------------

/** The resource editor's values; numbers are kept as typed. */
export interface ResourceForm {
  name: string;
  kind: ResourceKind;
  capacity: string;
  units: string;
  slotMinutes: string;
  bookingUnit: BookingUnit;
  isActive: boolean;
  /** False: the resource follows the business opening hours. */
  hasOwnSchedule: boolean;
}

export type ResourceFormErrors = Partial<Record<"name" | "capacity" | "units" | "slotMinutes", MessageKey>>;

export function emptyResourceForm(kind: ResourceKind, bookingUnit: BookingUnit): ResourceForm {
  return {
    name: "",
    kind,
    capacity: "",
    units: "1",
    slotMinutes: "",
    bookingUnit,
    isActive: true,
    hasOwnSchedule: false,
  };
}

export function resourceFormFromView(resource: ResourceView): ResourceForm {
  return {
    name: resource.name,
    kind: resource.kind,
    capacity: String(resource.capacity),
    units: String(resource.unit_count),
    slotMinutes: resource.slot_minutes ? String(resource.slot_minutes) : "",
    bookingUnit: resource.booking_unit,
    isActive: resource.is_active,
    hasOwnSchedule: (resource.schedule ?? []).length > 0,
  };
}

function wholeNumberError(text: string, min: number, max: number, optional: boolean): MessageKey | undefined {
  const trimmed = text.trim();
  if (trimmed === "") {
    return optional ? undefined : "validation.required";
  }
  if (!/^\d+$/.test(trimmed)) {
    return "validation.wholeNumber";
  }
  const value = Number(trimmed);
  if (value < min) {
    return "validation.positive";
  }
  return value > max ? "knowledge.resources.errors.tooLarge" : undefined;
}

export function validateResourceForm(form: ResourceForm): ResourceFormErrors {
  const errors: ResourceFormErrors = {};
  if (form.name.trim() === "") {
    errors.name = "validation.required";
  } else if (form.name.trim().length > 200) {
    errors.name = "validation.tooLong";
  }
  const capacity = wholeNumberError(form.capacity, 1, MAX_CAPACITY, false);
  const units = wholeNumberError(form.units, 1, MAX_UNITS, false);
  let slot = wholeNumberError(form.slotMinutes, 1, MAX_SLOT_MINUTES, true);
  if (slot === undefined && form.slotMinutes.trim() !== "" && Number(form.slotMinutes.trim()) < MIN_SLOT_MINUTES) {
    slot = "knowledge.resources.errors.slotTooShort";
  }
  return {
    ...errors,
    ...(capacity ? { capacity } : {}),
    ...(units ? { units } : {}),
    ...(slot ? { slotMinutes: slot } : {}),
  };
}

/** Body of POST …/resources; `schedule` is the resource's own weekly hours or empty. */
export function resourceCreateBody(form: ResourceForm, schedule: OpeningInterval[]): ResourceCreateBody {
  return {
    name: form.name.trim(),
    kind: form.kind,
    capacity: Number(form.capacity.trim()),
    unit_count: Number(form.units.trim()),
    slot_minutes: form.slotMinutes.trim() === "" ? null : Number(form.slotMinutes.trim()),
    booking_unit: form.bookingUnit,
    is_active: form.isActive,
    schedule: form.hasOwnSchedule ? schedule : [],
  };
}

function scheduleKey(schedule: readonly OpeningInterval[]): string {
  return [...schedule]
    .map((interval) => `${interval.weekday}:${interval.opens_at}-${interval.closes_at}`)
    .sort()
    .join(",");
}

/** Body of PATCH …/resources/{id}: only what changed (an empty schedule = business hours). */
export function resourcePatchBody(form: ResourceForm, resource: ResourceView, schedule: OpeningInterval[]): ResourcePatchBody {
  const next = resourceCreateBody(form, schedule);
  const patch: ResourcePatchBody = {};
  if (next.name !== resource.name) {
    patch.name = next.name;
  }
  if (next.kind !== resource.kind) {
    patch.kind = next.kind;
  }
  if (next.capacity !== resource.capacity) {
    patch.capacity = next.capacity;
  }
  if (next.unit_count !== resource.unit_count) {
    patch.unit_count = next.unit_count;
  }
  if ((next.slot_minutes ?? null) !== (resource.slot_minutes ?? null)) {
    patch.slot_minutes = next.slot_minutes ?? null;
  }
  if (next.booking_unit !== resource.booking_unit) {
    patch.booking_unit = next.booking_unit;
  }
  if (next.is_active !== resource.is_active) {
    patch.is_active = next.is_active;
  }
  const nextSchedule = next.schedule ?? [];
  if (scheduleKey(nextSchedule) !== scheduleKey(resource.schedule ?? [])) {
    patch.schedule = nextSchedule;
  }
  return patch;
}

/** Active resources first, then by name. */
export function sortResources(resources: readonly ResourceView[], locale: string): ResourceView[] {
  return [...resources].sort(
    (left, right) =>
      Number(right.is_active) - Number(left.is_active) || left.name.localeCompare(right.name, locale),
  );
}

// --- Local dates -------------------------------------------------------------------

const LOCAL_DATE = /^(\d{4})-(\d{2})-(\d{2})$/;

/** "2026-02-30" is not a date; "2026-02-28" is. */
export function isLocalDate(text: string): boolean {
  const match = LOCAL_DATE.exec(text);
  if (!match) {
    return false;
  }
  const [year, month, day] = [Number(match[1]), Number(match[2]), Number(match[3])];
  const date = new Date(Date.UTC(year, month - 1, day));
  return date.getUTCFullYear() === year && date.getUTCMonth() === month - 1 && date.getUTCDate() === day;
}

function utcDate(localDate: string): Date {
  const [year, month, day] = localDate.split("-").map(Number);
  return new Date(Date.UTC(year ?? 1970, (month ?? 1) - 1, day ?? 1));
}

/** Today's date in a time zone as "YYYY-MM-DD". */
export function todayInTimeZone(now: Date, timeZone: string): string {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(now);
  const part = (type: string) => parts.find((item) => item.type === type)?.value ?? "";
  return `${part("year")}-${part("month")}-${part("day")}`;
}

/** ISO weekday (Monday = 1) of a local date. */
export function weekdayOfDate(localDate: string): Weekday {
  const day = utcDate(localDate).getUTCDay();
  return (day === 0 ? 7 : day) as Weekday;
}

/** A local date as text in the UI language: "Thu, 31 Dec 2026". */
export function formatLocalDate(localDate: string, locale: string): string {
  return dateTimeFormat(locale, {
    weekday: "short",
    day: "numeric",
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  }).format(utcDate(localDate));
}

// --- Special hours ----------------------------------------------------------------

export interface TimeRangeRow {
  key: string;
  opens: string;
  closes: string;
}

export type SpecialHoursResult = { ok: true; intervals: OpeningInterval[] } | { ok: false; error: MessageKey };

/**
 * The intervals of one special-hours day. "00:00" as the closing time means
 * midnight; a day here cannot run past midnight (add the next day too).
 */
export function specialHoursIntervals(localDate: string, rows: readonly TimeRangeRow[]): SpecialHoursResult {
  if (rows.length === 0) {
    return { ok: false, error: "knowledge.exceptions.errors.hoursRequired" };
  }
  const weekday = weekdayOfDate(localDate);
  const intervals: OpeningInterval[] = [];
  for (const row of rows) {
    const opens = parseTimeOfDay(row.opens);
    const closesRaw = parseTimeOfDay(row.closes);
    if (opens === null || closesRaw === null) {
      return { ok: false, error: "validation.time" };
    }
    const closes = closesRaw === 0 ? 1440 : closesRaw;
    if (closes <= opens) {
      return { ok: false, error: "knowledge.exceptions.errors.closesBeforeOpens" };
    }
    intervals.push({ weekday, opens_at: opens, closes_at: closes });
  }
  intervals.sort((left, right) => left.opens_at - right.opens_at);
  for (let index = 1; index < intervals.length; index += 1) {
    const previous = intervals[index - 1];
    const current = intervals[index];
    if (previous && current && current.opens_at < previous.closes_at) {
      return { ok: false, error: "validation.hoursOverlap" };
    }
  }
  return { ok: true, intervals };
}

/** "10:00–16:00, 18:00–24:00". */
export function intervalsLabel(intervals: readonly Pick<OpeningInterval, "opens_at" | "closes_at">[]): string {
  return [...intervals]
    .sort((left, right) => left.opens_at - right.opens_at)
    .map((interval) => `${formatMinutesOfDay(interval.opens_at)}–${formatMinutesOfDay(interval.closes_at)}`)
    .join(", ");
}

/** Exceptions from today on (soonest first) and past ones (latest first). */
export function splitExceptions<T extends Pick<ScheduleExceptionView, "date">>(
  exceptions: readonly T[],
  today: string,
): { upcoming: T[]; past: T[] } {
  const sorted = [...exceptions].sort((left, right) => left.date.localeCompare(right.date));
  return {
    upcoming: sorted.filter((item) => item.date >= today),
    past: sorted.filter((item) => item.date < today).reverse(),
  };
}
