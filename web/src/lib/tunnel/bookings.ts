/**
 * "Hours and bookings" in the tunnel: the booking rules and the first
 * bookable place as a few plain choices (how long a visit is, how many
 * people, how much notice), prefilled from the niche's starter answers or
 * from what the business already saved, and the bodies sent to the API.
 */

import type { RequestBody, Schema } from "@/api/types";

type BookingRules = Schema<"BookingRules">;
type BookingRulesInput = Schema<"BookingRulesInput">;
type StarterResource = Schema<"StarterResourceView">;

/** Minutes of notice the owner picks from (none, an hour, three hours, a day). */
const NOTICE_CHOICES: readonly number[] = [0, 60, 180, 1440];
/** Visit lengths in minutes for niches that book time slots. */
const SLOT_CHOICES: readonly number[] = [15, 30, 45, 60, 90, 120, 180, 240];

export interface BookingForm {
  slotMinutes: number;
  maxPartySize: string;
  minNoticeMinutes: number;
  cancellationPolicy: string;
}

export interface ResourceForm {
  name: string;
  capacity: string;
  unitCount: string;
}

const DEFAULT_SLOT_MINUTES = 60;

/** The form from the stored rules, else the niche's suggestion, else plain defaults. */
export function bookingForm(stored: BookingRules | null | undefined, suggested: BookingRulesInput | null | undefined): BookingForm {
  const source = stored ?? suggested ?? null;
  return {
    slotMinutes: source?.slot_minutes ?? DEFAULT_SLOT_MINUTES,
    maxPartySize: String(source?.max_party_size ?? 1),
    minNoticeMinutes: source?.min_notice_minutes ?? 0,
    cancellationPolicy: source?.cancellation_policy ?? "",
  };
}

/** The visit lengths to offer: the usual ones plus the current value when it is unusual. */
export function slotChoices(current: number): number[] {
  return SLOT_CHOICES.includes(current) ? [...SLOT_CHOICES] : [...SLOT_CHOICES, current].sort((a, b) => a - b);
}

export function noticeChoices(current: number): number[] {
  return NOTICE_CHOICES.includes(current) ? [...NOTICE_CHOICES] : [...NOTICE_CHOICES, current].sort((a, b) => a - b);
}

const MAX_PARTY_SIZE = 10_000;
const MAX_UNITS = 1_000;

function wholeNumber(text: string, max: number): number | null {
  const trimmed = text.trim();
  if (!/^\d+$/.test(trimmed)) {
    return null;
  }
  const value = Number(trimmed);
  return value >= 1 && value <= max ? value : null;
}

export type BookingProblem = "partySize" | "capacity" | "unitCount" | "resourceName";

/**
 * The rules to save, or what is wrong. Night bookings (hotels, rentals)
 * keep the slot they had: a night is not chosen from visit lengths.
 * The deposit and the resource kind are kept as they were.
 */
export function bookingRulesInput(
  form: BookingForm,
  base: BookingRules | BookingRulesInput | null | undefined,
): { ok: true; rules: BookingRulesInput } | { ok: false; problem: BookingProblem } {
  const party = wholeNumber(form.maxPartySize, MAX_PARTY_SIZE);
  if (party === null) {
    return { ok: false, problem: "partySize" };
  }
  return {
    ok: true,
    rules: {
      resource_kind: base?.resource_kind ?? null,
      slot_minutes: form.slotMinutes,
      max_party_size: party,
      min_notice_minutes: form.minNoticeMinutes,
      deposit_minor: base?.deposit_minor ?? null,
      deposit_currency_code: base?.deposit_currency_code ?? null,
      cancellation_policy: form.cancellationPolicy.trim() || null,
    },
  };
}

export function resourceForm(suggested: StarterResource | null | undefined): ResourceForm {
  return {
    name: suggested?.name ?? "",
    capacity: String(suggested?.capacity ?? 1),
    unitCount: String(suggested?.unit_count ?? 1),
  };
}

export type ResourceBody = RequestBody<"/v1/businesses/{business_id}/resources", "post">;

/** The first bookable place to create, or what is wrong with the form. */
export function resourceBody(
  form: ResourceForm,
  suggested: StarterResource | null | undefined,
): { ok: true; body: ResourceBody } | { ok: false; problem: BookingProblem } {
  const name = form.name.trim();
  if (name === "") {
    return { ok: false, problem: "resourceName" };
  }
  const capacity = wholeNumber(form.capacity, MAX_PARTY_SIZE);
  if (capacity === null) {
    return { ok: false, problem: "capacity" };
  }
  const units = wholeNumber(form.unitCount, MAX_UNITS);
  if (units === null) {
    return { ok: false, problem: "unitCount" };
  }
  return {
    ok: true,
    body: {
      name,
      capacity,
      unit_count: units,
      ...(suggested ? { kind: suggested.kind, booking_unit: suggested.booking_unit } : {}),
      ...(suggested?.slot_minutes ? { slot_minutes: suggested.slot_minutes } : {}),
    },
  };
}

/** Whether the owner changed the suggested place (then it is created as typed). */
export function isResourceEdited(form: ResourceForm, suggested: StarterResource | null | undefined): boolean {
  const initial = resourceForm(suggested);
  return form.name.trim() !== initial.name || form.capacity.trim() !== initial.capacity || form.unitCount.trim() !== initial.unitCount;
}
