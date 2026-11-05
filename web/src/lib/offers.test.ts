import { describe, expect, it } from "vitest";

import {
  addDays,
  bookingValue,
  isBookableKind,
  isInSeason,
  isLinked,
  kindHasBuffer,
  linkedResourceNames,
  nightRate,
  offerBookingUnit,
  offerOfBooking,
  performersOf,
  servicesOf,
  sortOffers,
  stayValueMinor,
  type OfferItem,
  type OfferResource,
} from "./offers";

const item = (patch: Partial<OfferItem> & Pick<OfferItem, "id">): OfferItem => ({
  kind: "service",
  title: patch.id,
  is_active: true,
  ...patch,
});

const resource = (patch: Partial<OfferResource> & Pick<OfferResource, "id">): OfferResource => ({
  name: patch.id,
  kind: "staff",
  booking_unit: "time_slot",
  is_active: true,
  ...patch,
});

describe("bookable kinds", () => {
  it("knows which kinds are booked, have a break and go by the night", () => {
    expect(["service", "package", "room_type"].every((kind) => isBookableKind(kind as OfferItem["kind"]))).toBe(true);
    expect(isBookableKind("menu_item")).toBe(false);
    expect(kindHasBuffer("service")).toBe(true);
    expect(kindHasBuffer("package")).toBe(true);
    expect(kindHasBuffer("room_type")).toBe(false);
    expect(offerBookingUnit("room_type")).toBe("night");
    expect(offerBookingUnit("service")).toBe("time_slot");
  });
});

describe("performers", () => {
  const haircut = item({ id: "haircut", performer_resource_ids: ["nino"] });
  const nails = item({ id: "nails" });
  const beard = item({ id: "beard" });
  const nino = resource({ id: "nino", name: "Nino" });
  const lena = resource({ id: "lena", name: "Lena", serves_item_ids: ["nails"] });
  const giorgi = resource({ id: "giorgi", name: "Giorgi" });
  const off = resource({ id: "off", is_active: false, serves_item_ids: ["beard"] });

  it("links from either side", () => {
    expect(isLinked(haircut, nino)).toBe(true);
    expect(isLinked(nails, lena)).toBe(true);
    expect(isLinked(haircut, lena)).toBe(false);
    expect(isLinked(item({ id: "deluxe", kind: "room_type" }), resource({ id: "r1", room_type_item_id: "deluxe" }))).toBe(true);
  });

  it("offers the linked performers, else the generalists, else everyone booked that way", () => {
    const all = [nino, lena, giorgi];
    expect(performersOf(haircut, all, [haircut, nails])).toEqual([nino]);
    expect(performersOf(nails, all, [haircut, nails])).toEqual([lena]);
    // Nobody is linked to the beard: the masters linked to nothing take it.
    expect(performersOf(beard, all, [haircut, nails, beard])).toEqual([giorgi]);
    // Everyone is linked to something: every active master.
    expect(performersOf(beard, [nino, lena], [haircut, nails, beard])).toEqual([nino, lena]);
    // Only a switched-off master performs it: nobody can be booked.
    expect(performersOf(beard, [...all, off], [haircut, nails, beard])).toEqual([]);
  });

  it("keeps a room type to the rooms booked by the night", () => {
    const deluxe = item({ id: "deluxe", kind: "room_type" });
    const room = resource({ id: "r1", kind: "room", booking_unit: "night" });
    expect(performersOf(deluxe, [nino, room], [deluxe])).toEqual([room]);
  });

  it("names linked resources and the services of a resource", () => {
    expect(linkedResourceNames(haircut, [nino, lena])).toEqual(["Nino"]);
    const deluxe = item({ id: "deluxe", kind: "room_type", performer_resource_ids: ["lena"] });
    expect(servicesOf(lena, [haircut, nails, deluxe]).map((offer) => offer.id)).toEqual(["nails"]);
  });
});

describe("the booked offer and its value", () => {
  const deluxe = item({
    id: "deluxe",
    kind: "room_type",
    price_minor: 10000,
    seasonal_rates: [
      { starts_on: "06-01", ends_on: "08-31", nightly_rate_minor: 15000, name: "Summer" },
      { starts_on: "12-20", ends_on: "01-10", nightly_rate_minor: 20000 },
    ],
  });

  it("is the service asked for, else the room type of the room", () => {
    const haircut = item({ id: "haircut", price_minor: 3500 });
    expect(offerOfBooking("haircut", null, [haircut])).toBe(haircut);
    expect(offerOfBooking("missing", null, [haircut])).toBeNull();
    expect(offerOfBooking(null, { room_type_item_id: "deluxe" }, [haircut, deluxe])).toBe(deluxe);
    expect(offerOfBooking(null, { room_type_item_id: null }, [deluxe])).toBeNull();
    expect(offerOfBooking(null, null, [deluxe])).toBeNull();
  });

  it("prices nights by season, over New Year too", () => {
    expect(isInSeason("2026-07-15", { starts_on: "06-01", ends_on: "08-31" })).toBe(true);
    expect(isInSeason("2026-09-01", { starts_on: "06-01", ends_on: "08-31" })).toBe(false);
    expect(isInSeason("2027-01-05", { starts_on: "12-20", ends_on: "01-10" })).toBe(true);
    expect(isInSeason("2026-12-19", { starts_on: "12-20", ends_on: "01-10" })).toBe(false);
    expect(addDays("2026-12-31", 1)).toBe("2027-01-01");
    expect(nightRate(deluxe, "2026-08-31")).toBe(15000);
    expect(nightRate(deluxe, "2026-09-01")).toBe(10000);
    // Two summer nights and one at the plain rate.
    expect(stayValueMinor(deluxe, "2026-08-30", 3)).toBe(40000);
    expect(stayValueMinor(item({ id: "x", kind: "room_type" }), "2026-08-30", 1)).toBeNull();
  });

  it("values a service at its price and a stay at its nights", () => {
    expect(bookingValue(item({ id: "haircut", price_minor: 3500 }), { date: "2026-10-07", nights: null }, "EUR")).toEqual({
      minor: 3500,
      currency: "EUR",
    });
    expect(bookingValue(item({ id: "free" }), { date: "2026-10-07", nights: null }, "EUR")).toBeNull();
    expect(bookingValue(null, { date: "2026-10-07", nights: null }, "EUR")).toBeNull();
    expect(bookingValue({ ...deluxe, currency_code: "GEL" }, { date: "2026-08-31", nights: 2 }, "EUR")).toEqual({
      minor: 25000,
      currency: "GEL",
    });
    expect(bookingValue(deluxe, { date: "2026-09-01", nights: null }, "EUR")).toEqual({ minor: 10000, currency: "EUR" });
    expect(bookingValue(deluxe, { date: "", nights: 2 }, "EUR")).toBeNull();
  });
});

describe("sorting offers", () => {
  it("keeps active bookable offers by kind, then title", () => {
    const sorted = sortOffers(
      [
        item({ id: "b", title: "Brows" }),
        item({ id: "p", title: "Bridal", kind: "package" }),
        item({ id: "a", title: "alpha" }),
        item({ id: "r", title: "Deluxe", kind: "room_type" }),
        item({ id: "off", title: "Old", is_active: false }),
        item({ id: "faq", title: "Parking", kind: "faq" }),
      ],
      "en",
    );
    expect(sorted.map((offer) => offer.id)).toEqual(["a", "b", "r", "p"]);
  });
});
