/**
 * A guest books a table at the demo restaurant through its website chat
 * (the real widget API, the rehearsal model books the first free time) and
 * reads the written confirmation the chat shows: its manage link
 * (/r/{token}) leads to the guest's booking page.
 */

import { expect, type APIRequestContext } from "@playwright/test";

import { uniqueSuffix } from "./api";
import { API_URL } from "./env";

/** What the rehearsal model reads as "I want to book", per language. */
export const BOOKING_REQUESTS = {
  en: "Hello! I'd like to book a table, please.",
  ka: "გამარჯობა! მინდა მაგიდის დაჯავშნა.",
  he: "שלום! אני רוצה להזמין שולחן.",
} as const;

const MANAGE_LINK = /\/r\/([A-Za-z0-9_-]{40,120})/;

export interface GuestBooking {
  sessionKey: string;
  /** The confirmation as the chat shows it. */
  confirmation: string;
  token: string;
  /** "/r/{token}" on the cabinet. */
  path: string;
}

interface WidgetPoll {
  cursor?: string | null;
  items: { author: string; text: string }[];
}

async function poll(request: APIRequestContext, businessId: string, sessionKey: string, after?: string) {
  const response = await request.get(`${API_URL}/v1/widget/${businessId}/messages`, {
    headers: { "X-Widget-Session-Key": sessionKey },
    params: after ? { after } : {},
  });
  expect(response.ok(), await response.text()).toBe(true);
  return (await response.json()) as WidgetPoll;
}

/** The chat's messages after the visitor's latest own one. */
export async function chatAnswers(request: APIRequestContext, businessId: string, sessionKey: string): Promise<string[]> {
  const { cursor } = await poll(request, businessId, sessionKey);
  if (!cursor) {
    return [];
  }
  return (await poll(request, businessId, sessionKey, cursor)).items.map((item) => item.text);
}

/** The guest asks to book in `language`; the chat shows the confirmation with its link. */
export async function bookThroughWebChat(
  request: APIRequestContext,
  businessId: string,
  language: keyof typeof BOOKING_REQUESTS,
): Promise<GuestBooking> {
  const sessionKey = `e2e_${uniqueSuffix()}_guest`;
  const sent = await request.post(`${API_URL}/v1/widget/${businessId}/messages`, {
    data: { session_key: sessionKey, text: BOOKING_REQUESTS[language], contact_name: "Nino" },
  });
  expect(sent.status(), await sent.text()).toBe(202);

  let confirmation = "";
  await expect
    .poll(
      async () => {
        confirmation = (await chatAnswers(request, businessId, sessionKey)).find((text) => MANAGE_LINK.test(text)) ?? "";
        return confirmation;
      },
      { message: "the chat shows the written confirmation", timeout: 20_000 },
    )
    .toMatch(MANAGE_LINK);
  const token = MANAGE_LINK.exec(confirmation)![1]!;
  return { sessionKey, confirmation, token, path: `/r/${token}` };
}

/** The booking's local date ("2026-10-06") as the API's manage page reads it. */
export async function bookingDate(request: APIRequestContext, token: string): Promise<string> {
  const response = await request.get(`${API_URL}/v1/public/bookings/${token}`);
  expect(response.ok(), await response.text()).toBe(true);
  return ((await response.json()) as { date: string }).date;
}

/** The day after a local date: "2026-10-06" -> "2026-10-07". */
export function dayAfter(date: string): string {
  const next = new Date(`${date}T12:00:00Z`);
  next.setUTCDate(next.getUTCDate() + 1);
  return next.toISOString().slice(0, 10);
}
