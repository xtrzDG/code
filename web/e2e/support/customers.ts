/**
 * Customers for the Customers and command palette tests, made through the
 * real API: a master who works every day and a booking added by hand,
 * which makes its guest a customer with a phone number.
 */

import { expect, type APIRequestContext } from "@playwright/test";

import { API_URL } from "./env";

const EVERY_DAY = [1, 2, 3, 4, 5, 6, 7].map((weekday) => ({ weekday, opens_at: 9 * 60, closes_at: 20 * 60 }));

export interface BookedCustomer {
  contactId: string;
  name: string;
  phone: string;
}

function headersOf(token: string) {
  return { authorization: `Bearer ${token}` };
}

/** "YYYY-MM-DD" a few days from now (the salon's zone does not matter at noon). */
function dayAhead(days: number): string {
  return new Date(Date.now() + days * 24 * 60 * 60 * 1000).toISOString().slice(0, 10);
}

async function addMaster(request: APIRequestContext, token: string, businessId: string): Promise<string> {
  const response = await request.post(`${API_URL}/v1/businesses/${businessId}/resources`, {
    data: { name: "Lena", kind: "staff", capacity: 1, schedule: EVERY_DAY },
    headers: headersOf(token),
  });
  expect(response.status(), await response.text()).toBe(201);
  return ((await response.json()) as { id: string }).id;
}

/** A customer who booked by phone with the front desk; returns them with their contact id. */
export async function bookedCustomer(
  request: APIRequestContext,
  token: string,
  businessId: string,
  customer: { name: string; phone: string },
): Promise<BookedCustomer> {
  const resourceId = await addMaster(request, token, businessId);
  const booked = await request.post(`${API_URL}/v1/businesses/${businessId}/bookings`, {
    data: {
      contact_name: customer.name,
      contact_phone_number: customer.phone,
      date: dayAhead(3),
      time: "12:00",
      party_size: 2,
      duration_minutes: 60,
      resource_id: resourceId,
    },
    headers: headersOf(token),
  });
  expect(booked.status(), await booked.text()).toBe(201);

  const listed = await request.get(`${API_URL}/v1/businesses/${businessId}/contacts`, {
    params: { search: customer.name },
    headers: headersOf(token),
  });
  expect(listed.ok(), await listed.text()).toBe(true);
  const items = ((await listed.json()) as { items: { id: string; name?: string | null }[] }).items;
  const contact = items.find((item) => item.name === customer.name);
  expect(contact, "the booking made its guest a customer").toBeDefined();
  return { contactId: contact!.id, ...customer };
}
