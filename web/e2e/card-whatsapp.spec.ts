/**
 * WhatsApp replies after the 24-hour window: sent in the owner's template,
 * a template WhatsApp refuses or a missing one pointing to the Channels page,
 * and setting the template there. The card and the channel list are served by
 * the test (see support/conversation-card.ts); everything else runs against
 * the real API.
 */

import type { Schema } from "../src/api/types";

import { expect, test } from "./support/fixtures";
import { en } from "./support/messages";
import { CONVERSATION_ID, conversationCard, HOUR_US, openCard, serveCard } from "./support/conversation-card";

type ChannelView = Schema<"ChannelView">;

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

  await openCard(page, owner.businessId);
  await expect(page.getByText(en.conversations.reply.template.intro)).toBeVisible();
  await expect(page.getByText(/“staff_reply”/)).toBeVisible();
  await page.getByLabel(en.conversations.reply.label).fill("Sua mesa está reservada.\nAté sábado!");
  await page.getByRole("button", { name: en.conversations.reply.template.send }).click();

  await expect(page.getByText(en.conversations.reply.template.sent)).toBeVisible();
  expect(sent).toEqual([{ text: "Sua mesa está reservada.\nAté sábado!", as_template: true }]);
  await expect(page.getByText("Sua mesa está reservada. Até sábado!")).toBeVisible();
});

test("a template WhatsApp refused shows on the reply and points the owner to the Channels page", async ({
  page,
  owner,
}) => {
  const card = conversationCard(owner.businessId, {
    reply: {
      is_available: false,
      block: "window_closed",
      template: { name: "staff_reply", language_code: "en", max_text_length: 1024 },
    },
  });
  // The worker gave the reply up: Meta refused the template (its outbox
  // message failed with `template_rejected`).
  await serveCard(page, owner.businessId, {
    ...card,
    messages: [
      ...(card.messages ?? []),
      {
        id: "message_6b5a4c3d-2e1f-4a0b-9c8d-7e6f5a4b3c2d",
        direction: "outbound",
        author: "staff",
        text: "Your table is ready.",
        tool_calls: [],
        input_tokens: 0,
        output_tokens: 0,
        cost_micro_usd: 0,
        created_at: Date.now() * 1000 - HOUR_US,
        delivery: { state: "failed", failure_reason: "template_rejected", attempts: 1 },
      },
    ],
  });

  await openCard(page, owner.businessId);

  const chip = page.locator('[data-delivery-state="failed"]');
  await expect(chip).toContainText(en.messageDelivery.states.failed);
  await expect(chip).toContainText(en.messageDelivery.reasons.template_rejected);
  const rejected = en.conversations.reply.template.rejectedOwner.replace("{name}", "staff_reply");
  // Not "try again": the box says what to fix.
  const inline = page
    .getByRole("alert")
    .filter({ hasText: rejected })
    .filter({ has: page.getByRole("link", { name: en.conversations.reply.openChannels }) });
  await expect(inline).toBeVisible();
  await expect(inline.getByRole("link", { name: en.conversations.reply.openChannels })).toHaveAttribute(
    "href",
    `/b/${owner.businessId}/assistant/channels`,
  );
});

test("without a template the closed window points to the Channels page", async ({ page, owner }) => {
  await serveCard(page, owner.businessId, conversationCard(owner.businessId, {}));

  await openCard(page, owner.businessId);

  await expect(page.getByText(en.conversations.reply.noTemplateOwner)).toBeVisible();
  await expect(page.getByRole("link", { name: en.conversations.reply.openChannels })).toHaveAttribute(
    "href",
    `/b/${owner.businessId}/assistant/channels`,
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

  await page.goto(`/b/${owner.businessId}/assistant/channels`);
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
