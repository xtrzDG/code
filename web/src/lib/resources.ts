/**
 * Pure helpers of bookable resources (Knowledge -> "Resources and hours"):
 * the resource editor's form, its API bodies and the list order. Holidays
 * and special-hours days are in specialDays.ts.
 */

import type { OpeningInterval, RequestBody, ResourceKind, Schema } from "@/api/types";
import type { MessageKey } from "@/i18n/translate";

export type ResourceView = Schema<"ResourceView">;
export type BookingUnit = Schema<"BookingUnit">;
export type ResourceCreateBody = RequestBody<"/v1/businesses/{business_id}/resources", "post">;
export type ResourcePatchBody = RequestBody<"/v1/businesses/{business_id}/resources/{resource_id}", "patch">;

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
  /** The services and packages it performs (booked by time). */
  serviceIds: string[];
  /** The room type a room is of (booked by the night); "" for none. */
  roomTypeId: string;
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
    serviceIds: [],
    roomTypeId: "",
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
    serviceIds: [...(resource.serves_item_ids ?? [])],
    roomTypeId: resource.room_type_item_id ?? "",
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

/**
 * Body of POST …/resources; `schedule` is the resource's own weekly hours
 * or empty. A resource booked by time performs services; one booked by the
 * night is a room of a room type (the other link is left empty).
 */
export function resourceCreateBody(form: ResourceForm, schedule: OpeningInterval[]): ResourceCreateBody {
  const isNightly = form.bookingUnit === "night";
  return {
    name: form.name.trim(),
    kind: form.kind,
    capacity: Number(form.capacity.trim()),
    unit_count: Number(form.units.trim()),
    slot_minutes: form.slotMinutes.trim() === "" ? null : Number(form.slotMinutes.trim()),
    booking_unit: form.bookingUnit,
    is_active: form.isActive,
    schedule: form.hasOwnSchedule ? schedule : [],
    serves_item_ids: isNightly ? [] : [...new Set(form.serviceIds)],
    room_type_item_id: isNightly && form.roomTypeId ? form.roomTypeId : null,
  };
}

function sameIds(left: readonly string[], right: readonly string[]): boolean {
  return left.length === right.length && [...left].sort().join(",") === [...right].sort().join(",");
}

function scheduleKey(schedule: readonly OpeningInterval[]): string {
  return [...schedule]
    .map((interval) => `${interval.weekday}:${interval.opens_at}-${interval.closes_at}`)
    .sort()
    .join(",");
}

/**
 * Body of PATCH …/resources/{id}: only what changed (an empty schedule =
 * business hours; a new services list is the whole truth, null clears the
 * room type).
 */
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
  if (!sameIds(next.serves_item_ids ?? [], resource.serves_item_ids ?? [])) {
    patch.serves_item_ids = next.serves_item_ids ?? [];
  }
  if ((next.room_type_item_id ?? null) !== (resource.room_type_item_id ?? null)) {
    patch.room_type_item_id = next.room_type_item_id ?? null;
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
