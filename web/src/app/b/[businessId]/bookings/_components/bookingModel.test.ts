import { describe, expect, it } from "vitest";

import type { BookingView } from "@/components/insights/types";

import {
  bookingActions,
  bookingApiQuery,
  bookingEditValues,
  bookingFiltersQuery,
  bookingUnitFor,
  canChangePlacement,
  customerLanguage,
  DEFAULT_BOOKING_FILTERS,
  groupBookingsByDate,
  groupSlotsByResource,
  isRangeValid,
  nightsOf,
  parseBookingFilters,
  placesForEdit,
  rangeDates,
  reminderState,
  validateBookingEdit,
  validateBookingForm,
  type BookingFormValues,
} from "./bookingModel";

function booking(id: string, date: string, time: string | null): BookingView {
  return {
    id,
    business_id: "business_1",
    resource_id: "resource_1",
    resource_name: "Table",
    contact_id: "contact_1",
    contact_name: null,
    contact_phone_number: null,
    date,
    time,
    end_date: date,
    end_time: null,
    timezone: "Asia/Tbilisi",
    party_size: 2,
    status: "confirmed",
    source_channel: "phone",
    notes: null,
    is_sandbox: false,
    created_at: 1_790_000_000_000_000,
  };
}

describe("booking ranges", () => {
  const today = "2026-10-01";

  it("turn presets into local dates", () => {
    expect(rangeDates({ range: "upcoming", from: null, to: null }, today)).toEqual({ from: today, to: null });
    expect(rangeDates({ range: "today", from: null, to: null }, today)).toEqual({ from: today, to: today });
    expect(rangeDates({ range: "tomorrow", from: null, to: null }, today)).toEqual({ from: "2026-10-02", to: "2026-10-02" });
    expect(rangeDates({ range: "week", from: null, to: null }, today)).toEqual({ from: today, to: "2026-10-07" });
    expect(rangeDates({ range: "past", from: null, to: null }, today)).toEqual({ from: "2026-09-01", to: "2026-09-30" });
    expect(rangeDates({ range: "custom", from: "2026-11-01", to: null }, today)).toEqual({ from: "2026-11-01", to: null });
  });

  it("reject a start after the end", () => {
    expect(isRangeValid({ from: "2026-10-02", to: "2026-10-01" })).toBe(false);
    expect(isRangeValid({ from: "2026-10-01", to: null })).toBe(true);
  });
});

describe("booking filters in the URL", () => {
  it("round-trip and drop invalid values", () => {
    const filters = { ...DEFAULT_BOOKING_FILTERS, range: "custom" as const, from: "2026-10-01", to: "2026-10-07", status: "pending" as const };
    const query = bookingFiltersQuery(filters);
    expect(query).toBe("range=custom&from=2026-10-01&to=2026-10-07&status=pending");
    expect(parseBookingFilters(Object.fromEntries(new URLSearchParams(query)))).toEqual(filters);
    expect(parseBookingFilters({ range: "decade", from: "2026-13-01", status: "lost", test: ["1", "1"] })).toEqual(
      DEFAULT_BOOKING_FILTERS,
    );
    expect(bookingFiltersQuery(DEFAULT_BOOKING_FILTERS)).toBe("");
  });
});

describe("grouping", () => {
  it("groups by day and orders by time", () => {
    const days = groupBookingsByDate([
      booking("late", "2026-10-02", "20:00"),
      booking("next", "2026-10-03", "12:00"),
      booking("early", "2026-10-02", "09:30"),
    ]);
    expect(days.map((day) => [day.date, day.bookings.map((item) => item.id)])).toEqual([
      ["2026-10-02", ["early", "late"]],
      ["2026-10-03", ["next"]],
    ]);
    expect(groupBookingsByDate([booking("a", "2026-09-01", null), booking("b", "2026-09-02", null)], { newestFirst: true })[0]?.date).toBe(
      "2026-09-02",
    );
  });

  it("counts nights of stays", () => {
    expect(nightsOf({ date: "2026-10-01", end_date: "2026-10-04" })).toBe(3);
    expect(nightsOf({ date: "2026-10-01", end_date: "2026-10-01" })).toBe(0);
  });
});

describe("actions", () => {
  it("allow changes only to active bookings", () => {
    expect(bookingActions("pending")).toEqual({ confirm: true, complete: true, noShow: true, reschedule: true, cancel: true });
    expect(bookingActions("confirmed").confirm).toBe(false);
    expect(Object.values(bookingActions("cancelled")).some(Boolean)).toBe(false);
    expect(Object.values(bookingActions("completed")).some(Boolean)).toBe(false);
  });
});

describe("booking unit", () => {
  const resources = [
    { id: "room", booking_unit: "night" as const, is_active: true },
    { id: "table", booking_unit: "time_slot" as const, is_active: true },
  ];

  it("follows the chosen resource, else nights only when every resource is booked by nights", () => {
    expect(bookingUnitFor(resources, "room")).toBe("night");
    expect(bookingUnitFor(resources, "")).toBe("time_slot");
    expect(bookingUnitFor([resources[0]!], "")).toBe("night");
    expect(bookingUnitFor([], "")).toBe("time_slot");
  });
});

describe("manual booking form", () => {
  const values: BookingFormValues = {
    contactName: "  Nino ",
    phone: " 599 11 22 33 ",
    date: "2026-10-03",
    time: "20:00",
    nights: "",
    partySize: "4",
    resourceId: "",
    notes: "",
    source: "phone",
    language: "ka",
    country: "IT",
  };

  it("builds the API body for a time slot", () => {
    expect(validateBookingForm(values, "time_slot")).toEqual({
      ok: true,
      body: {
        contact_name: "Nino",
        contact_phone_number: "599 11 22 33",
        resource_id: null,
        date: "2026-10-03",
        time: "20:00",
        nights: null,
        party_size: 4,
        notes: null,
        source_channel: "phone",
        language: "ka",
        country_hint: "IT",
      },
    });
  });

  it("asks for nights instead of a time for stays", () => {
    const result = validateBookingForm({ ...values, time: "", nights: "3", resourceId: "room" }, "night");
    expect(result.ok && result.body).toMatchObject({ time: null, nights: 3, resource_id: "room" });
    expect(validateBookingForm({ ...values, nights: "0" }, "night")).toEqual({
      ok: false,
      errors: { nights: "bookings.errors.nights" },
    });
  });

  it("reports every missing field", () => {
    expect(validateBookingForm({ ...values, contactName: " ", date: "", time: "", partySize: "0" }, "time_slot")).toEqual({
      ok: false,
      errors: {
        contactName: "bookings.errors.nameRequired",
        date: "bookings.errors.dateRequired",
        partySize: "bookings.errors.partySize",
        time: "bookings.errors.timeRequired",
      },
    });
  });
});

describe("list query", () => {
  it("sends every filter to the API and reads past ranges latest first", () => {
    expect(bookingApiQuery(DEFAULT_BOOKING_FILTERS, { from: "2026-10-01", to: null })).toEqual({
      from: "2026-10-01",
      order: "earliest_first",
    });
    expect(
      bookingApiQuery(
        { ...DEFAULT_BOOKING_FILTERS, range: "past", status: "no_show", resourceId: "resource_9", includeTest: true },
        { from: "2026-09-01", to: "2026-09-30" },
      ),
    ).toEqual({
      from: "2026-09-01",
      to: "2026-09-30",
      status: "no_show",
      resource_id: "resource_9",
      include_sandbox: "true",
      order: "latest_first",
    });
  });
});

describe("booking details", () => {
  it("uses the customer's language when the business speaks it", () => {
    const business = { languages: ["ka", "en"], default_language: "ka" };
    expect(customerLanguage({ language: "en" }, business)).toBe("en");
    expect(customerLanguage({ language: "de" }, business)).toBe("ka");
    expect(customerLanguage({ language: null }, business)).toBe("ka");
  });

  it("tells whether the reminder went out or is still to come", () => {
    const upcoming = { ...booking("a", "2026-10-03", "20:00"), status: "confirmed" as const };
    expect(reminderState(upcoming, "2026-10-01")).toBe("pending");
    expect(reminderState({ ...upcoming, reminder_sent_at: 1 }, "2026-10-01")).toBe("sent");
    expect(reminderState({ ...upcoming, status: "cancelled" }, "2026-10-01")).toBe("none");
    expect(reminderState(upcoming, "2026-10-04")).toBe("none");
  });

  it("groups whole-day slots by place in the order they come", () => {
    const slot = (resource: string, time: string) => ({
      resource_id: resource,
      resource_name: resource.toUpperCase(),
      booking_unit: "time_slot" as const,
      date: "2026-10-03",
      time,
    });
    const groups = groupSlotsByResource([slot("t2", "12:00"), slot("t4", "12:00"), slot("t2", "12:30")]);
    expect(groups.map((group) => [group.resourceName, group.slots.map((item) => item.time)])).toEqual([
      ["T2", ["12:00", "12:30"]],
      ["T4", ["12:00"]],
    ]);
  });
});

describe("booking edit", () => {
  const current = { ...booking("a", "2026-10-03", "20:00"), contact_name: "Nino", party_size: 2, notes: "Window" };

  it("sends only what changed", () => {
    const values = bookingEditValues(current);
    expect(validateBookingEdit(values, current)).toEqual({ ok: true, body: null });
    expect(
      validateBookingEdit({ ...values, partySize: "5", resourceId: "resource_2", notes: "", contactName: " Nino B. " }, current),
    ).toEqual({
      ok: true,
      body: { party_size: 5, resource_id: "resource_2", notes: "", contact_name: "Nino B." },
    });
  });

  it("refuses an empty name and a bad party size", () => {
    expect(validateBookingEdit({ ...bookingEditValues(current), contactName: " " }, current)).toEqual({
      ok: false,
      errors: { contactName: "bookings.errors.nameRequired" },
    });
    expect(validateBookingEdit({ ...bookingEditValues(current), partySize: "0" }, current)).toEqual({
      ok: false,
      errors: { partySize: "bookings.errors.partySize" },
    });
  });

  it("offers active places booked the same way and only for upcoming bookings", () => {
    const places = [
      { id: "resource_1", name: "Table", booking_unit: "time_slot" as const, is_active: true },
      { id: "resource_2", name: "Terrace", booking_unit: "time_slot" as const, is_active: true },
      { id: "room", name: "Room", booking_unit: "night" as const, is_active: true },
      { id: "old", name: "Old", booking_unit: "time_slot" as const, is_active: false },
    ];
    expect(placesForEdit(places, current).map((place) => place.id)).toEqual(["resource_1", "resource_2"]);
    expect(canChangePlacement("confirmed")).toBe(true);
    expect(canChangePlacement("completed")).toBe(false);
  });
});
