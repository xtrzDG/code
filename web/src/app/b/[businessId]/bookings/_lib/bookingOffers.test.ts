import { describe, expect, it } from "vitest";

import type { ResourceView } from "@/components/insights/types";
import type { OfferItem } from "@/lib/offers";

import { booking } from "./bookingFixtures";
import { bookingValueText } from "./bookingList";
import { bookedOffer, offerPickerKind, placesForOffer, withOffer } from "./bookingOffers";
import type { BookingFormValues } from "./manualBooking";

const resource = (id: string, patch: Partial<ResourceView> = {}): ResourceView => ({
  id,
  business_id: "business_1",
  kind: "staff",
  name: id,
  capacity: 1,
  unit_count: 1,
  booking_unit: "time_slot",
  is_active: true,
  created_at: 0,
  updated_at: 0,
  ...patch,
});

const haircut: OfferItem = { id: "haircut", kind: "service", title: "Haircut", is_active: true, duration_minutes: 45, price_minor: 3500 };
const nails: OfferItem = { id: "nails", kind: "service", title: "Nails", is_active: true, duration_minutes: 60 };
const deluxe: OfferItem = { id: "deluxe", kind: "room_type", title: "Deluxe", is_active: true, price_minor: 10000 };

const nino = resource("nino", { serves_item_ids: ["haircut"] });
const lena = resource("lena", { serves_item_ids: ["nails"] });
const room = resource("r1", { kind: "room", booking_unit: "night", room_type_item_id: "deluxe" });

const values: BookingFormValues = {
  contactName: "Mariam",
  phone: "",
  date: "2026-10-07",
  time: "",
  nights: "1",
  partySize: "1",
  resourceId: "",
  serviceId: "",
  duration: "",
  notes: "",
  source: "phone",
  language: "en",
  country: "GE",
};

describe("the service picker", () => {
  it("offers only the performers of the chosen service", () => {
    expect(placesForOffer(haircut, [nino, lena], [haircut, nails]).map((place) => place.id)).toEqual(["nino"]);
    expect(placesForOffer(null, [nino, lena, resource("off", { is_active: false })], []).map((place) => place.id)).toEqual(["nino", "lena"]);
  });

  it("fills in the usual length and drops a place that does not perform it", () => {
    expect(withOffer({ ...values, resourceId: "lena" }, haircut, [nino, lena], [haircut, nails])).toMatchObject({
      serviceId: "haircut",
      duration: "45",
      resourceId: "",
    });
    expect(withOffer({ ...values, resourceId: "nino" }, haircut, [nino, lena], [haircut, nails]).resourceId).toBe("nino");
    expect(withOffer({ ...values, serviceId: "haircut", duration: "45" }, null, [nino], [haircut])).toMatchObject({
      serviceId: "",
      duration: "",
    });
  });

  it("is labelled as a room type only when every offer is one", () => {
    expect(offerPickerKind([deluxe])).toBe("roomType");
    expect(offerPickerKind([deluxe, haircut])).toBe("service");
    expect(offerPickerKind([])).toBe("service");
  });

  it("values a booking by the chosen offer, else by the room's type", () => {
    expect(bookedOffer({ serviceId: "haircut", resourceId: "" }, [nino], [haircut, deluxe])).toBe(haircut);
    expect(bookedOffer({ serviceId: "", resourceId: "r1" }, [room], [haircut, deluxe])).toBe(deluxe);
    expect(bookedOffer({ serviceId: "", resourceId: "" }, [room], [deluxe])).toBeNull();
  });
});

describe("the value of a listed booking", () => {
  const money = (minor: number, currency?: string) => `${currency ?? "?"} ${minor / 100}`;

  it("shows the booked value in its currency, nothing without one", () => {
    expect(bookingValueText({ ...booking("b", "2026-10-07", "11:00"), value_minor: 3500, currency_code: "EUR" }, money)).toBe("EUR 35");
    expect(bookingValueText(booking("b", "2026-10-07", "11:00"), money)).toBeNull();
    expect(bookingValueText({ value_minor: 0, currency_code: null }, money)).toBe("? 0");
  });
});
