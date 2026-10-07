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

  it("follows the chosen offer first: a room type goes by the night, a service by time", () => {
    expect(bookingUnitFor(resources, "table", { kind: "room_type" })).toBe("night");
    expect(bookingUnitFor(resources, "room", { kind: "service" })).toBe("time_slot");
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
    serviceId: "",
    duration: "",
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
        service_item_id: null,
        duration_minutes: null,
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

describe("booking a service", () => {
  const values: BookingFormValues = {
    contactName: "Mariam",
    phone: "",
    date: "2026-10-07",
    time: "11:00",
    nights: "1",
    partySize: "1",
    resourceId: "nino",
    serviceId: "haircut",
    duration: "45",
    notes: "",
    source: "phone",
    language: "ka",
    country: "GE",
  };

  it("names the service and sends a length only when staff changed it", () => {
    const usual = validateBookingForm(values, "time_slot", { duration_minutes: 45 });
    expect(usual.ok && usual.body).toMatchObject({ service_item_id: "haircut", resource_id: "nino", duration_minutes: null });
    const longer = validateBookingForm({ ...values, duration: "60" }, "time_slot", { duration_minutes: 45 });
    expect(longer.ok && longer.body).toMatchObject({ duration_minutes: 60 });
    const empty = validateBookingForm({ ...values, duration: "" }, "time_slot", { duration_minutes: 45 });
    expect(empty.ok && empty.body).toMatchObject({ duration_minutes: null });
  });

  it("checks the length: 5 minutes to 30 days", () => {
    expect(validateBookingForm({ ...values, duration: "3" }, "time_slot")).toEqual({
      ok: false,
      errors: { duration: "bookings.errors.duration" },
    });
    expect(validateBookingForm({ ...values, duration: "x" }, "time_slot")).toEqual({
      ok: false,
      errors: { duration: "bookings.errors.duration" },
    });
  });

  it("books a room type by the night without a length", () => {
    const stay = validateBookingForm({ ...values, serviceId: "deluxe", resourceId: "", nights: "3" }, "night", { duration_minutes: null });
    expect(stay.ok && stay.body).toMatchObject({ service_item_id: "deluxe", nights: 3, time: null, duration_minutes: null });
  });
});
