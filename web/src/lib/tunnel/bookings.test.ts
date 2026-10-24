import { describe, expect, it } from "vitest";

import type { Schema } from "@/api/types";

import {
  bookingForm,
  bookingRulesInput,
  isResourceEdited,
  noticeChoices,
  resourceBody,
  resourceForm,
  slotChoices,
} from "./bookings";

const SUGGESTED: Schema<"BookingRulesInput"> = {
  resource_kind: "staff",
  slot_minutes: 60,
  max_party_size: 1,
  min_notice_minutes: 60,
  cancellation_policy: "Tell us 3 hours ahead.",
};

const STORED: Schema<"BookingRules"> = {
  resource_kind: "table",
  slot_minutes: 90,
  max_party_size: 8,
  min_notice_minutes: 0,
  deposit_minor: 1000,
  deposit_currency_code: "EUR",
};

const RESOURCE: Schema<"StarterResourceView"> = {
  kind: "staff",
  booking_unit: "time_slot",
  name: "Master",
  capacity: 1,
  unit_count: 2,
};

describe("booking choices", () => {
  it("start from what is stored, else the suggestion, else defaults", () => {
    expect(bookingForm(STORED, SUGGESTED)).toEqual({ slotMinutes: 90, maxPartySize: "8", minNoticeMinutes: 0, cancellationPolicy: "" });
    expect(bookingForm(null, SUGGESTED)).toEqual({
      slotMinutes: 60,
      maxPartySize: "1",
      minNoticeMinutes: 60,
      cancellationPolicy: "Tell us 3 hours ahead.",
    });
    expect(bookingForm(undefined, undefined)).toEqual({ slotMinutes: 60, maxPartySize: "1", minNoticeMinutes: 0, cancellationPolicy: "" });
  });

  it("offer the usual lengths and notices, plus an unusual current one", () => {
    expect(slotChoices(60)).not.toContain(75);
    expect(slotChoices(75)).toContain(75);
    expect(noticeChoices(60)).toEqual([0, 60, 180, 1440]);
    expect(noticeChoices(30)).toEqual([0, 30, 60, 180, 1440]);
  });

  it("become rules that keep the deposit and the kind", () => {
    const result = bookingRulesInput({ slotMinutes: 45, maxPartySize: " 4 ", minNoticeMinutes: 180, cancellationPolicy: "  " }, STORED);
    expect(result).toEqual({
      ok: true,
      rules: {
        resource_kind: "table",
        slot_minutes: 45,
        max_party_size: 4,
        min_notice_minutes: 180,
        deposit_minor: 1000,
        deposit_currency_code: "EUR",
        cancellation_policy: null,
      },
    });
    const fresh = bookingRulesInput(bookingForm(null, SUGGESTED), null);
    expect(fresh.ok && fresh.rules.resource_kind).toBeNull();
  });

  it("refuse a party size that is not a whole positive number", () => {
    for (const text of ["", "0", "2.5", "abc", "20000"]) {
      expect(bookingRulesInput({ ...bookingForm(null, SUGGESTED), maxPartySize: text }, null)).toEqual({ ok: false, problem: "partySize" });
    }
  });
});

describe("the first bookable place", () => {
  it("starts from the suggestion", () => {
    expect(resourceForm(RESOURCE)).toEqual({ name: "Master", capacity: "1", unitCount: "2" });
    expect(resourceForm(null)).toEqual({ name: "", capacity: "1", unitCount: "1" });
  });

  it("knows when the owner changed it", () => {
    expect(isResourceEdited(resourceForm(RESOURCE), RESOURCE)).toBe(false);
    expect(isResourceEdited({ ...resourceForm(RESOURCE), unitCount: "3" }, RESOURCE)).toBe(true);
    expect(isResourceEdited({ ...resourceForm(RESOURCE), name: "Stylist" }, RESOURCE)).toBe(true);
    expect(isResourceEdited({ ...resourceForm(RESOURCE), capacity: "2" }, RESOURCE)).toBe(true);
  });

  it("becomes the create body with the niche's kind", () => {
    expect(resourceBody({ name: " Stylist ", capacity: "1", unitCount: "3" }, RESOURCE)).toEqual({
      ok: true,
      body: { name: "Stylist", capacity: 1, unit_count: 3, kind: "staff", booking_unit: "time_slot" },
    });
    expect(resourceBody({ name: "Room", capacity: "2", unitCount: "1" }, { ...RESOURCE, slot_minutes: 1440 })).toEqual({
      ok: true,
      body: { name: "Room", capacity: 2, unit_count: 1, kind: "staff", booking_unit: "time_slot", slot_minutes: 1440 },
    });
    expect(resourceBody({ name: "Room", capacity: "2", unitCount: "1" }, null)).toEqual({
      ok: true,
      body: { name: "Room", capacity: 2, unit_count: 1 },
    });
  });

  it("says what is wrong with the form", () => {
    expect(resourceBody({ name: " ", capacity: "1", unitCount: "1" }, RESOURCE)).toEqual({ ok: false, problem: "resourceName" });
    expect(resourceBody({ name: "A", capacity: "0", unitCount: "1" }, RESOURCE)).toEqual({ ok: false, problem: "capacity" });
    expect(resourceBody({ name: "A", capacity: "1", unitCount: "x" }, RESOURCE)).toEqual({ ok: false, problem: "unitCount" });
  });
});
