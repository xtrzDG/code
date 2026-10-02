import { describe, expect, it } from "vitest";

import { bookingUnitFor, validateBookingForm, type BookingFormValues } from "./manualBooking";

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
