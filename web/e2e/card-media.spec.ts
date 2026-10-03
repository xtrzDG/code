/**
 * What customers send besides text, in the conversation card: a voice
 * message shows what the assistant heard and is fetched only when played, a
 * photo opens full size, a place links to a map, and what the assistant
 * could not read (a sticker) or a file the retention purge removed says so.
 * The card is served by the test (support/conversation-card.ts); the media
 * files are answered by the test too.
 */

import AxeBuilder from "@axe-core/playwright";
import type { Page, Route } from "@playwright/test";

import type { Schema } from "../src/api/types";

import { expect, test } from "./support/fixtures";
import { CONVERSATION_ID, HOUR_US, conversationCard, openCard, serveCard, silentWav, type ConversationDetail } from "./support/conversation-card";
import { en } from "./support/messages";
import { findOverflow } from "./support/overflow";

const VOICE_ID = "media_5a1d2c3b-4e5f-4a6b-8c7d-9e0f1a2b3c4d";
const PHOTO_ID = "media_6b2e3d4c-5f6a-4b7c-9d8e-0f1a2b3c4d5e";
const TRANSCRIPT = "Hi! Is there a table for four tonight at seven?";
const PURGED_TRANSCRIPT = "And do you have a children's menu?";
const CAPTION = "Is this the khachapuri you serve?";
const MAP_URL = "https://maps.google.com/?q=41.693438,44.801525";
// A 1x1 PNG.
const ONE_PIXEL_PNG = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==",
  "base64",
);

type Message = Schema<"MessageView">;

function customerMessage(index: number, text: string, attachments: Message["attachments"]): Message {
  return {
    id: `message_0d1c2b3a-4e5f-4a6b-9c7d-8e9f0a1b2c${String(index).padStart(2, "0")}`,
    direction: "inbound",
    author: "customer",
    text,
    tool_calls: [],
    input_tokens: 0,
    output_tokens: 0,
    cost_micro_usd: 0,
    created_at: Date.now() * 1000 - (10 - index) * HOUR_US,
    attachments,
  };
}

function cardWithMedia(businessId: string): ConversationDetail {
  const card = conversationCard(businessId, {
    messages: [
      customerMessage(1, "", [
        { kind: "audio", media_id: VOICE_ID, media_type: "audio/ogg", duration_seconds: 7, transcript: TRANSCRIPT, is_media_deleted: false },
      ]),
      customerMessage(2, "", [{ kind: "audio", duration_seconds: 4, transcript: PURGED_TRANSCRIPT, is_media_deleted: true }]),
      customerMessage(3, CAPTION, [{ kind: "image", media_id: PHOTO_ID, media_type: "image/png", is_media_deleted: false }]),
      customerMessage(4, "", [
        {
          kind: "location",
          location: { latitude: 41.693438, longitude: 44.801525, name: "Freedom Square", address: "Tbilisi" },
          map_url: MAP_URL,
          is_media_deleted: false,
        },
      ]),
      customerMessage(5, "", [{ kind: "sticker", problem: "unsupported_kind", is_media_deleted: false }]),
    ],
  });
  card.conversation.channel = "telegram";
  card.conversation.contact_name = "Ana Souza";
  return card;
}

async function serveMedia(page: Page, photoStatus = 200): Promise<string[]> {
  const fetched: string[] = [];
  await page.route("**/api/backend/v1/businesses/*/media/*", (route: Route) => {
    const url = route.request().url();
    fetched.push(url);
    if (url.endsWith(PHOTO_ID)) {
      return photoStatus === 200
        ? route.fulfill({ status: 200, contentType: "image/png", body: ONE_PIXEL_PNG })
        : route.fulfill({ status: photoStatus, json: { error: "not_found", message: "This file is no longer kept." } });
    }
    return route.fulfill({ status: 200, contentType: "audio/wav", body: silentWav(7) });
  });
  return fetched;
}

test("a voice message shows its transcript and is fetched only when played", async ({ page, owner }) => {
  await serveCard(page, owner.businessId, cardWithMedia(owner.businessId));
  const fetched = await serveMedia(page);
  await openCard(page, owner.businessId);

  await expect(page.getByText(TRANSCRIPT)).toBeVisible();
  await expect(page.getByText("0:07")).toBeVisible();
  // The purged voice message keeps its words but cannot be played.
  await expect(page.getByText(PURGED_TRANSCRIPT)).toBeVisible();
  await expect(page.getByText(en.conversationMedia.deleted)).toBeVisible();
  const play = page.getByRole("button", { name: en.conversationMedia.voice.playLabel });
  await expect(play).toHaveCount(1);
  expect(fetched.filter((url) => url.endsWith(VOICE_ID))).toEqual([]);

  await play.click();
  const player = page.getByLabel(en.conversationMedia.voice.playerLabel);
  await expect(player).toBeFocused();
  expect(await player.evaluate((audio: HTMLAudioElement) => audio.src.startsWith("blob:"))).toBe(true);
  expect(fetched.filter((url) => url.endsWith(VOICE_ID))).toHaveLength(1);
});

test("a photo opens full size, a place links to the map, a sticker says why it was not read", async ({ page, owner }) => {
  await serveCard(page, owner.businessId, cardWithMedia(owner.businessId));
  await serveMedia(page);
  await openCard(page, owner.businessId);

  const alt = en.conversationMedia.photo.altWithCaption.replace("{caption}", CAPTION);
  const thumbnail = page.getByRole("img", { name: alt });
  await expect(thumbnail).toBeVisible();
  await expect.poll(() => thumbnail.evaluate((image: HTMLImageElement) => image.naturalWidth)).toBe(1);
  await page.getByRole("button", { name: en.conversationMedia.photo.open }).click();
  const viewer = page.getByRole("dialog", { name: en.conversationMedia.photo.viewerTitle });
  await expect(viewer.getByRole("img", { name: alt })).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(viewer).toBeHidden();

  const map = page.getByRole("link", { name: en.conversationMedia.place.openMapLabel.replace("{place}", "Freedom Square") });
  await expect(map).toHaveAttribute("href", MAP_URL);
  await expect(map).toHaveAttribute("target", "_blank");
  await expect(map).toHaveAttribute("rel", "noopener noreferrer");
  await expect(page.getByText("41.69344, 44.80152")).toBeVisible();

  await expect(page.getByText(en.conversationMedia.kinds.sticker)).toBeVisible();
  await expect(page.getByText(en.conversationMedia.problems.unsupported_kind)).toBeVisible();

  const results = await new AxeBuilder({ page })
    .include("[data-transcript]")
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
    .analyze();
  expect(results.violations).toEqual([]);
});

test("a photo that is gone leaves a note, and the card fits a phone", async ({ page, owner, consoleErrors }) => {
  consoleErrors.allow(/Failed to load resource: the server responded with a status of 404/);
  await page.setViewportSize({ width: 390, height: 844 });
  await serveCard(page, owner.businessId, cardWithMedia(owner.businessId));
  await serveMedia(page, 404);
  await page.goto(`/b/${owner.businessId}/inbox/${CONVERSATION_ID}`);

  await expect(page.getByText(en.conversationMedia.photo.unavailable)).toBeVisible();
  await expect(page.getByText(TRANSCRIPT)).toBeVisible();
  expect(await findOverflow(page)).toEqual([]);
});
