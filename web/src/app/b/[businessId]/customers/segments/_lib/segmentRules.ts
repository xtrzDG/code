/**
 * Saved segments: the editor's form and its checks (the API's limits), the
 * body it sends, a stable key of the rules for the live count, and the
 * rules as a short sentence ("tag “regular” · last visit over 60 days ago").
 */

import type { RequestBody, Schema } from "@/api/types";
import type { MessageKey, PluralKey } from "@/i18n/translate";

export type Segment = Schema<"SegmentView">;
export type SegmentList = Schema<"SegmentList">;
export type SegmentRules = Schema<"SegmentRulesBody">;
export type SegmentPreview = Schema<"SegmentPreview">;
export type SegmentBody = RequestBody<"/v1/businesses/{business_id}/customer-segments", "post">;

export const MAX_SEGMENTS = 50;
export const MAX_SEGMENT_NAME = 60;
const MAX_DAYS = 3650;
const MAX_BOOKINGS = 10_000;

/** What the editor's fields hold: numbers stay text until saved. */
export interface SegmentForm {
  name: string;
  tag: string;
  lastVisitDays: string;
  minBookings: string;
  maxBookings: string;
  vipOnly: boolean;
}

export type SegmentField = "name" | "lastVisitDays" | "minBookings" | "maxBookings";
export type SegmentErrors = Partial<Record<SegmentField, MessageKey>>;

export const EMPTY_SEGMENT_FORM: SegmentForm = {
  name: "",
  tag: "",
  lastVisitDays: "",
  minBookings: "",
  maxBookings: "",
  vipOnly: false,
};

const numberText = (value: number | null | undefined) => (value === null || value === undefined ? "" : String(value));

/** The form of a saved segment. */
export function formOf(segment: Segment): SegmentForm {
  return {
    name: segment.name,
    tag: segment.rules.tag ?? "",
    lastVisitDays: numberText(segment.rules.last_visit_days_ago),
    minBookings: numberText(segment.rules.min_bookings),
    maxBookings: numberText(segment.rules.max_bookings),
    vipOnly: segment.rules.vip_only ?? false,
  };
}

/** A single line without control characters, spaces at the ends or runs of spaces. */
function cleanLine(text: string): string {
  return text
    .replace(/[\u0000-\u001f\u007f]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

/** A whole number in range from a field, null when empty, "bad" otherwise. */
function wholeNumber(text: string, min: number, max: number): number | null | "bad" {
  const trimmed = text.trim();
  if (trimmed === "") {
    return null;
  }
  if (!/^\d+$/.test(trimmed)) {
    return "bad";
  }
  const value = Number(trimmed);
  return value >= min && value <= max ? value : "bad";
}

/** The rules of the form (the live count asks with them even before a name is given). */
export function rulesOf(form: SegmentForm): { rules: SegmentRules | null; errors: SegmentErrors } {
  const errors: SegmentErrors = {};
  const days = wholeNumber(form.lastVisitDays, 1, MAX_DAYS);
  const min = wholeNumber(form.minBookings, 0, MAX_BOOKINGS);
  const max = wholeNumber(form.maxBookings, 0, MAX_BOOKINGS);
  if (days === "bad") {
    errors.lastVisitDays = "segments.errors.days";
  }
  if (min === "bad") {
    errors.minBookings = "segments.errors.bookings";
  }
  if (max === "bad") {
    errors.maxBookings = "segments.errors.bookings";
  }
  if (typeof min === "number" && typeof max === "number" && min > max) {
    errors.maxBookings = "segments.errors.minMax";
  }
  if (Object.keys(errors).length > 0) {
    return { rules: null, errors };
  }
  const tag = cleanLine(form.tag).slice(0, 32).trim();
  return {
    rules: {
      tag: tag === "" ? null : tag,
      last_visit_days_ago: days === "bad" ? null : days,
      min_bookings: min === "bad" ? null : min,
      max_bookings: max === "bad" ? null : max,
      vip_only: form.vipOnly,
    },
    errors,
  };
}

/** The body to save, or the errors to show next to the fields. */
export function segmentBody(form: SegmentForm): { body: SegmentBody | null; errors: SegmentErrors } {
  const { rules, errors } = rulesOf(form);
  const name = cleanLine(form.name);
  const allErrors: SegmentErrors = { ...errors };
  if (name === "" || name.length > MAX_SEGMENT_NAME) {
    allErrors.name = "segments.errors.name";
  }
  if (!rules || allErrors.name) {
    return { body: null, errors: allErrors };
  }
  return { body: { name, rules }, errors: allErrors };
}

/** The same rules give the same key (the live count's cache). */
export function rulesKey(rules: SegmentRules): string {
  return JSON.stringify([
    rules.tag?.toLowerCase() ?? null,
    rules.last_visit_days_ago ?? null,
    rules.min_bookings ?? null,
    rules.max_bookings ?? null,
    rules.vip_only ?? false,
  ]);
}

export type SummaryPart =
  | { key: MessageKey; values?: Record<string, string> }
  | { plural: PluralKey; count: number };

/** The rules as parts of a sentence; "Every customer" when none is set. */
export function summaryParts(rules: SegmentRules): SummaryPart[] {
  const parts: SummaryPart[] = [];
  if (rules.tag) {
    parts.push({ key: "segments.summary.tag", values: { tag: rules.tag } });
  }
  if (typeof rules.last_visit_days_ago === "number") {
    parts.push({ plural: "segments.summary.lastVisit", count: rules.last_visit_days_ago });
  }
  if (typeof rules.min_bookings === "number") {
    parts.push({ plural: "segments.summary.minBookings", count: rules.min_bookings });
  }
  if (typeof rules.max_bookings === "number") {
    parts.push({ plural: "segments.summary.maxBookings", count: rules.max_bookings });
  }
  if (rules.vip_only) {
    parts.push({ key: "segments.summary.vipOnly" });
  }
  return parts.length > 0 ? parts : [{ key: "segments.summary.everyone" }];
}
