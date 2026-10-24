/**
 * The team inbox through the API, for test setup and for checks the UI
 * cannot make: which conversation a visitor's is, who handles it, a
 * device subscribed to notifications, what the API says a card holds.
 */

import { expect, type APIRequestContext } from "@playwright/test";

import { API_URL } from "./env";
import type { Receiver } from "./push";

function headersOf(token: string) {
  return { authorization: `Bearer ${token}` };
}

/** The signed-in user's id. */
export async function userIdOf(request: APIRequestContext, token: string): Promise<string> {
  const response = await request.get(`${API_URL}/v1/me`, { headers: headersOf(token) });
  expect(response.ok(), await response.text()).toBe(true);
  return ((await response.json()) as { user: { id: string } }).user.id;
}

/** The conversation of the customer named `name` among those waiting for a person. */
export async function waitingConversationOf(
  request: APIRequestContext,
  token: string,
  businessId: string,
  name: string,
): Promise<string> {
  const response = await request.get(`${API_URL}/v1/businesses/${businessId}/inbox`, {
    params: { view: "needs_person", limit: "50" },
    headers: headersOf(token),
  });
  expect(response.ok(), await response.text()).toBe(true);
  const items = ((await response.json()) as { items: { id: string; contact_name?: string | null }[] }).items;
  const conversation = items.find((item) => item.contact_name === name);
  expect(conversation, `${name} waits for a person`).toBeDefined();
  return conversation!.id;
}

interface CardSnapshot {
  assignment: { assignee_user_id?: string | null; assignment_revision: number } | null;
  messages: { author: string; text: string }[];
  handoffs: { status: string }[];
}

/** The conversation card as the API gives it. */
export async function cardOf(
  request: APIRequestContext,
  token: string,
  businessId: string,
  conversationId: string,
): Promise<CardSnapshot> {
  const response = await request.get(`${API_URL}/v1/businesses/${businessId}/conversations/${conversationId}`, {
    headers: headersOf(token),
  });
  expect(response.ok(), await response.text()).toBe(true);
  const card = (await response.json()) as Partial<CardSnapshot>;
  return { assignment: card.assignment ?? null, messages: card.messages ?? [], handoffs: card.handoffs ?? [] };
}

/** Assigns the conversation to `assigneeUserId` (null: nobody), as of its current revision. */
export async function assignByApi(
  request: APIRequestContext,
  token: string,
  businessId: string,
  conversationId: string,
  assigneeUserId: string | null,
): Promise<void> {
  const { assignment } = await cardOf(request, token, businessId, conversationId);
  const response = await request.post(`${API_URL}/v1/businesses/${businessId}/conversations/${conversationId}/assign`, {
    data: { assignee_user_id: assigneeUserId, expected_revision: assignment?.assignment_revision ?? 0 },
    headers: headersOf(token),
  });
  expect(response.ok(), await response.text()).toBe(true);
}

/** Subscribes a device of the signed-in user to the business's notifications, at a test push service. */
export async function subscribeDevice(
  request: APIRequestContext,
  token: string,
  businessId: string,
  endpoint: string,
  receiver: Receiver,
): Promise<void> {
  const response = await request.post(`${API_URL}/v1/businesses/${businessId}/push-subscriptions`, {
    data: {
      endpoint,
      keys: { p256dh: receiver.publicKey.toString("base64url"), auth: receiver.auth.toString("base64url") },
      language: "en",
    },
    headers: headersOf(token),
  });
  expect(response.status(), await response.text()).toBe(201);
}
