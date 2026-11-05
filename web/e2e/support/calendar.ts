/**
 * Setup for the bookings calendar specs, through the API: places booked by
 * time or by the night, bookings and stays added by hand, a booking as the
 * API has it now, and dates in Berlin (the salon's zone).
 */

import { expect, type APIRequestContext } from "@playwright/test";

import { API_URL } from "./env";

const BERLIN = "Europe/Berlin";
const EVERY_DAY = [1, 2, 3, 4, 5, 6, 7].map((weekday) => ({ weekday, opens_at: 9 * 60, closes_at: 20 * 60 }));

function headersOf(token: string) {
  return { authorization: `Bearer ${token}` };
}

/** A local date in Berlin `days` from today. */
export function berlinDate(days: number): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone: BERLIN, year: "numeric", month: "2-digit", day: "2-digit" }).format(
    new Date(Date.now() + days * 24 * 60 * 60 * 1000),
  );
}

/** A place booked by time (a master working 9 to 20 every day) or by the night (rooms); returns its id. */
export async function addPlace(
  request: APIRequestContext,
  owner: { token: string; businessId: string },
  place: { name: string; byNight?: boolean; units?: number },
): Promise<string> {
  const data = place.byNight
    ? { name: place.name, kind: "room", capacity: 2, unit_count: place.units ?? 1, booking_unit: "night" }
    : { name: place.name, kind: "staff", capacity: 1, schedule: EVERY_DAY };
  const response = await request.post(`${API_URL}/v1/businesses/${owner.businessId}/resources`, {
    data,
    headers: headersOf(owner.token),
  });
  expect(response.status(), await response.text()).toBe(201);
  return ((await response.json()) as { id: string }).id;
}

export interface CalendarBooking {
  id: string;
  date: string;
  time: string | null;
  end_date: string;
  resource_id: string;
  resource_name: string;
}

/** A booking added by hand: an hour at `time`, or a stay of `nights` from `date`. */
export async function bookByHand(
  request: APIRequestContext,
  owner: { token: string; businessId: string },
  booking: { name: string; date: string; resourceId: string; time?: string; nights?: number },
): Promise<CalendarBooking> {
  const response = await request.post(`${API_URL}/v1/businesses/${owner.businessId}/bookings`, {
    data: {
      contact_name: booking.name,
      date: booking.date,
      ...(booking.nights ? { nights: booking.nights } : { time: booking.time, duration_minutes: 60 }),
      party_size: 1,
      resource_id: booking.resourceId,
      source_channel: "phone",
    },
    headers: headersOf(owner.token),
  });
  expect(response.status(), await response.text()).toBe(201);
  return ((await response.json()) as { booking: CalendarBooking }).booking;
}

/** The booking as the API has it now (from its date's list). */
export async function bookingNow(
  request: APIRequestContext,
  owner: { token: string; businessId: string },
  bookingId: string,
  around: string,
): Promise<CalendarBooking | null> {
  const response = await request.get(`${API_URL}/v1/businesses/${owner.businessId}/bookings`, {
    params: { from: around, limit: "100" },
    headers: headersOf(owner.token),
  });
  expect(response.ok(), await response.text()).toBe(true);
  const items = ((await response.json()) as { items: CalendarBooking[] }).items;
  return items.find((item) => item.id === bookingId) ?? null;
}
