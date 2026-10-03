/**
 * A conversation card served by the test itself: a call with a recording or
 * a WhatsApp chat past its 24-hour window can only come from the voice
 * platform and Meta, so the card's own API call (the BFF path the browser
 * uses) is answered with a view shaped like the API's.
 */

import { expect, type Page } from "@playwright/test";

import type { Schema } from "../../src/api/types";

import { en } from "./messages";

export type ConversationDetail = Schema<"ConversationDetailView">;

export const CONVERSATION_ID = "conversation_7f0c2a52-1d4b-4c3e-9a7e-2b6f1c9d0e11";
export const HOUR_US = 3600 * 1_000_000;

/** Seconds of silence as a WAV file (what the player is given). */
export function silentWav(seconds = 0.5): Buffer {
  const rate = 8000;
  const samples = Math.round(rate * seconds);
  const header = Buffer.alloc(44);
  header.write("RIFF", 0);
  header.writeUInt32LE(36 + samples * 2, 4);
  header.write("WAVEfmt ", 8);
  header.writeUInt32LE(16, 16);
  header.writeUInt16LE(1, 20);
  header.writeUInt16LE(1, 22);
  header.writeUInt32LE(rate, 24);
  header.writeUInt32LE(rate * 2, 28);
  header.writeUInt16LE(2, 32);
  header.writeUInt16LE(16, 34);
  header.write("data", 36);
  header.writeUInt32LE(samples * 2, 40);
  return Buffer.concat([header, Buffer.alloc(samples * 2)]);
}

export function conversationCard(businessId: string, overrides: Partial<ConversationDetail>): ConversationDetail {
  const wroteAt = Date.now() * 1000 - 30 * HOUR_US;
  return {
    conversation: {
      id: CONVERSATION_ID,
      business_id: businessId,
      contact_id: "contact_3c1d9a8e-5b2f-4e7a-8c6d-0f1e2d3c4b5a",
      assistant_version_id: "assistant_version_9b8a7c6d-5e4f-4a3b-8c2d-1e0f9a8b7c6d",
      channel: "whatsapp",
      status: "open",
      is_after_hours: false,
      is_sandbox: false,
      message_count: 1,
      customer_message_count: 1,
      contact_name: "Ana Souza",
      language: "pt",
      last_message_at: wroteAt,
      created_at: wroteAt,
    },
    messages: [
      {
        id: "message_0d1c2b3a-4e5f-4a6b-9c7d-8e9f0a1b2c3d",
        direction: "inbound",
        author: "customer",
        text: "Olá, ainda têm mesa para sábado?",
        tool_calls: [],
        input_tokens: 0,
        output_tokens: 0,
        cost_micro_usd: 0,
        created_at: wroteAt,
      },
    ],
    calls: [],
    bookings: [],
    leads: [],
    handoffs: [],
    reply: { is_available: false, block: "window_closed" },
    ...overrides,
  };
}

/** Answers the card's API call with `card` (or what it returns at each call). */
export async function serveCard(
  page: Page,
  businessId: string,
  card: ConversationDetail | (() => ConversationDetail),
): Promise<void> {
  await page.route(`**/api/backend/v1/businesses/${businessId}/conversations/${CONVERSATION_ID}`, (route) =>
    route.fulfill({ json: typeof card === "function" ? card() : card }),
  );
  // The team's notes load with the card; a served conversation has none.
  await page.route(`**/api/backend/v1/businesses/${businessId}/conversations/${CONVERSATION_ID}/notes*`, (route) =>
    route.fulfill({ json: { items: [], next_cursor: null } }),
  );
}

/** The served conversation, opened in the inbox. */
export async function openCard(page: Page, businessId: string): Promise<void> {
  await page.goto(`/b/${businessId}/inbox/${CONVERSATION_ID}`);
}

/**
 * Opens the conversation's details (calls, bookings, requests): a panel
 * next to the transcript on very wide screens, a sheet on the suite's
 * 1280 px window and on phones.
 */
export async function openDetails(page: Page, customerName = "Ana Souza"): Promise<void> {
  await page
    .getByRole("button", { name: en.inboxCard.openDetailsOf.replace("{name}", customerName), exact: true })
    .click();
  await expect(page.getByRole("dialog", { name: en.inboxCard.panelLabel })).toBeVisible();
}

export function playerLabel(): RegExp {
  return new RegExp(`^${en.conversations.calls.playerLabel.replace("{date}", ".+")}$`);
}

export function datedLabel(template: string): RegExp {
  return new RegExp(`^${template.replace("{date}", ".+")}$`);
}

export function cardWithCalls(businessId: string, callIds: string[]): ConversationDetail {
  const card = conversationCard(businessId, {
    calls: callIds.map((id, index) => ({
      id,
      started_at: Date.now() * 1000 - (3 - index) * HOUR_US,
      duration_seconds: 95,
      outcome: "information",
      recording_path: `elevenlabs/conversations/conv_${id}`,
    })),
    reply: { is_available: false, block: "voice_call" },
  });
  card.conversation.channel = "phone";
  return card;
}
