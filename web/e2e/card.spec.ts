/**
 * The conversation card's call recordings and WhatsApp template replies.
 *
 * A call with a recording or a WhatsApp chat past its 24-hour window can
 * only come from the voice platform and Meta, so these tests answer the
 * card's own API calls (the BFF paths the browser uses) with views shaped
 * like the API's; everything else runs against the real API.
 */

import type { Page, Route } from "@playwright/test";

import type { Schema } from "../src/api/types";

import { expect, test } from "./support/fixtures";
import { en } from "./support/messages";

type ConversationDetail = Schema<"ConversationDetailView">;
type ChannelView = Schema<"ChannelView">;

const CONVERSATION_ID = "conversation_7f0c2a52-1d4b-4c3e-9a7e-2b6f1c9d0e11";
const HOUR_US = 3600 * 1_000_000;

/** Half a second of silence as a WAV file (what the player is given). */
function silentWav(): Buffer {
  const rate = 8000;
  const samples = rate / 2;
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

function conversationCard(businessId: string, overrides: Partial<ConversationDetail>): ConversationDetail {
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

async function serveCard(page: Page, businessId: string, card: ConversationDetail): Promise<void> {
  await page.route(`**/api/backend/v1/businesses/${businessId}/conversations/${CONVERSATION_ID}`, (route) =>
    route.fulfill({ json: card }),
  );
}

function playerLabel(): RegExp {
  return new RegExp(`^${en.conversations.calls.playerLabel.replace("{date}", ".+")}$`);
}

test("a call recording loads only when played, and a missing one says so", async ({ page, owner, consoleErrors }) => {
  consoleErrors.allow(/Failed to load resource: the server responded with a status of 404/);
  const card = conversationCard(owner.businessId, {
    calls: [
      {
        id: "call_kept",
        started_at: Date.now() * 1000 - 3 * HOUR_US,
        duration_seconds: 95,
        outcome: "information",
        recording_path: "elevenlabs/conversations/conv_kept",
      },
      {
        id: "call_purged",
        started_at: Date.now() * 1000 - 2 * HOUR_US,
        duration_seconds: 40,
        recording_path: "elevenlabs/conversations/conv_purged",
      },
    ],
    reply: { is_available: false, block: "voice_call" },
  });
  card.conversation.channel = "phone";
  await serveCard(page, owner.businessId, card);
  const played: string[] = [];
  await page.route("**/calls/*/recording", (route: Route) => {
    const url = route.request().url();
    played.push(url);
    return url.includes("/calls/call_kept/")
      ? route.fulfill({ status: 200, contentType: "audio/wav", body: silentWav() })
      : route.fulfill({ status: 404, json: { error: "not_found", message: "This call has no recording." } });
  });

  await page.goto(`/b/${owner.businessId}/conversations/${CONVERSATION_ID}`);
  const players = page.getByLabel(playerLabel());
  await expect(players).toHaveCount(2);
  await page.waitForLoadState("networkidle");
  // Opening the card fetches no audio (and so writes no audit entry).
  expect(played).toEqual([]);

  await players.nth(0).evaluate((audio: HTMLAudioElement) => {
    audio.muted = true;
    return audio.play();
  });
  await expect.poll(() => players.nth(0).evaluate((audio: HTMLAudioElement) => audio.readyState)).toBeGreaterThan(1);
  expect(played).toHaveLength(1);
  await expect(page.getByText(en.conversations.calls.playError)).toBeHidden();

  await players.nth(1).evaluate((audio: HTMLAudioElement) => audio.play().catch(() => undefined));
  const failure = page.getByRole("alert").filter({ hasText: en.conversations.calls.playError });
  await expect(failure).toBeVisible();
  await expect(failure.getByRole("button", { name: en.conversations.calls.playRetry })).toBeVisible();
});

test("after 24 hours a WhatsApp reply goes out in the owner's template", async ({ page, owner }) => {
  await serveCard(
    page,
    owner.businessId,
    conversationCard(owner.businessId, {
      reply: {
        is_available: false,
        block: "window_closed",
        template: { name: "staff_reply", language_code: "pt_BR", max_text_length: 1024 },
      },
    }),
  );
  const sent: unknown[] = [];
  await page.route(`**/conversations/${CONVERSATION_ID}/messages`, (route) => {
    const body: unknown = route.request().postDataJSON();
    sent.push(body);
    return route.fulfill({
      status: 201,
      json: {
        delivery: "sent_as_template",
        message: {
          id: "message_5a4b3c2d-1e0f-4a9b-8c7d-6e5f4a3b2c1d",
          direction: "outbound",
          author: "staff",
          text: "Sua mesa está reservada. Até sábado!",
          tool_calls: [],
          input_tokens: 0,
          output_tokens: 0,
          cost_micro_usd: 0,
          created_at: Date.now() * 1000,
        },
      } satisfies Schema<"StaffMessageResult">,
    });
  });

  await page.goto(`/b/${owner.businessId}/conversations/${CONVERSATION_ID}`);
  await expect(page.getByText(en.conversations.reply.template.intro)).toBeVisible();
  await expect(page.getByText(/“staff_reply”/)).toBeVisible();
  await page.getByLabel(en.conversations.reply.label).fill("Sua mesa está reservada.\nAté sábado!");
  await page.getByRole("button", { name: en.conversations.reply.template.send }).click();

  await expect(page.getByText(en.conversations.reply.template.sent)).toBeVisible();
  expect(sent).toEqual([{ text: "Sua mesa está reservada.\nAté sábado!", as_template: true }]);
  await expect(page.getByText("Sua mesa está reservada. Até sábado!")).toBeVisible();
});

test("without a template the closed window points to the Channels page", async ({ page, owner }) => {
  await serveCard(page, owner.businessId, conversationCard(owner.businessId, {}));

  await page.goto(`/b/${owner.businessId}/conversations/${CONVERSATION_ID}`);

  await expect(page.getByText(en.conversations.reply.noTemplateOwner)).toBeVisible();
  await expect(page.getByRole("link", { name: en.conversations.reply.openChannels })).toHaveAttribute(
    "href",
    `/b/${owner.businessId}/channels`,
  );
  await expect(page.getByRole("button", { name: en.conversations.reply.template.send })).toHaveCount(0);
});

test("the owner sets the WhatsApp template for staff replies on the Channels page", async ({ page, owner }) => {
  const whatsapp: ChannelView = {
    id: "channel_4d3c2b1a-0f9e-4d8c-b7a6-5f4e3d2c1b0a",
    business_id: owner.businessId,
    channel: "whatsapp",
    status: "connected",
    account_id: "106540352242922",
    has_credential: false,
    updated_at: Date.now() * 1000,
  };
  await page.route(`**/api/backend/v1/businesses/${owner.businessId}/channels`, (route) =>
    route.fulfill({ json: [whatsapp] }),
  );
  const saved: unknown[] = [];
  await page.route(`**/api/backend/v1/businesses/${owner.businessId}/channels/whatsapp/staff-template`, (route) => {
    const body = route.request().postDataJSON() as { name: string; language_code: string };
    saved.push(body);
    return route.fulfill({ json: { ...whatsapp, staff_reply_template: body } });
  });

  await page.goto(`/b/${owner.businessId}/channels`);
  const card = page.getByRole("region", { name: en.channels.kinds.whatsapp, exact: true });
  await expect(card.getByText(en.channels.staffTemplate.notSet)).toBeVisible();

  await card.getByLabel(en.channels.staffTemplate.name, { exact: true }).fill("Staff Reply");
  await card.getByLabel(en.channels.staffTemplate.language, { exact: true }).fill("pt-br");
  await card.getByRole("button", { name: en.channels.staffTemplate.save }).click();
  await expect(card.getByText(en.channels.staffTemplate.nameInvalid)).toBeVisible();
  expect(saved).toEqual([]);

  await card.getByLabel(en.channels.staffTemplate.name, { exact: true }).fill("staff_reply");
  await card.getByRole("button", { name: en.channels.staffTemplate.save }).click();

  await expect(page.getByText(en.channels.staffTemplate.savedToast)).toBeVisible();
  expect(saved).toEqual([{ name: "staff_reply", language_code: "pt_BR" }]);
  await expect(card.getByText("staff_reply (pt_BR)")).toBeVisible();
  await expect(card.getByRole("button", { name: en.channels.staffTemplate.remove })).toBeVisible();
});
