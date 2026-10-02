import { describe, expect, it } from "vitest";

import { bookingEditValues, canChangePlacement, placesForEdit, validateBookingEdit } from "./bookingEdit";
import { booking } from "./bookingFixtures";

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
