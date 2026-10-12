/**
 * Photos, voice messages and the thumbs of the website chat widget on a
 * host site, against a fake widget API (support/widget-media.ts): the
 * paperclip uploads a photo the next message names (a thumbnail in the
 * log), a refused file says why, the microphone records while held, and
 * the thumbs show under a booking's answer at once or after two quiet
 * minutes, in English, Georgian and Hebrew.
 */

import type { Page } from "@playwright/test";

import { expect, test } from "./support/fixtures";
import { FakeMediaWidgetApi, PNG_PHOTO } from "./support/widget-media";
import { SITE, ask, chat, loadWidgetSource, serveSite } from "./support/widget-site";

test.beforeAll(async () => {
  await loadWidgetSource();
});

function speaks(api: FakeMediaWidgetApi, tag: string, direction: "ltr" | "rtl", name: string): void {
  api.configExtras = {
    ...api.configExtras,
    languages: [{ tag, direction, native_name: name }],
    default_language: tag,
  };
}

function photo(name = "menu.png", mimeType = "image/png") {
  return { name, mimeType, buffer: PNG_PHOTO };
}

test("a photo goes with the message and stays in the log as a thumbnail", async ({ page }) => {
  const api = new FakeMediaWidgetApi();
  await serveSite(page.context(), api, { dataOpen: true });
  await page.goto(`${SITE}/`);
  await expect(chat(page).getByRole("button", { name: "Attach a photo" })).toBeVisible();

  await page.locator("input[type=file]").setInputFiles(photo());

  await expect(chat(page).locator(".aw-tray img[alt='Photo']")).toBeVisible();
  const send = chat(page).getByRole("button", { name: "Send" });
  await expect(send).toBeEnabled();
  await send.click();

  await expect(chat(page).locator(".aw-visitor img.aw-thumb[alt='Photo']")).toBeVisible();
  await expect(chat(page).getByText("Answer to 1 file(s)")).toBeVisible();
  expect(api.uploads).toHaveLength(1);
  expect(api.uploads[0]?.contentType).toBe("image/png");
  // The visitor key travels in a header of the upload, never in its address.
  expect(api.uploads[0]?.sessionKey).toMatch(/^v1_/);
  expect(api.sentAttachments).toEqual([["widget_upload_00000000-0000-4000-8000-000000000001"]]);
  await expect(chat(page).locator(".aw-tray")).toBeHidden();
});

test("a file that is not a photo or that the API refuses is not sent", async ({ page, consoleErrors }) => {
  consoleErrors.allow(/status of 422/);
  const api = new FakeMediaWidgetApi();
  await serveSite(page.context(), api, { dataOpen: true });
  await page.goto(`${SITE}/`);
  const refusal = chat(page).getByText("Only photos and voice messages can be sent.");

  // Checked in the browser first: a GIF never leaves it.
  await page.locator("input[type=file]").setInputFiles(photo("party.gif", "image/gif"));
  await expect(refusal).toBeVisible();
  expect(api.uploads).toEqual([]);

  // Then by the API, from the file's bytes.
  api.refuseUploadWith = "type_mismatch";
  await page.locator("input[type=file]").setInputFiles(photo("renamed.png"));
  await expect(refusal).toBeVisible();
  expect(api.uploads).toHaveLength(1);
  await expect(chat(page).locator(".aw-tray img")).toHaveCount(0);
  await expect(chat(page).getByRole("button", { name: "Send" })).toBeDisabled();
});

test("in Georgian a booking's answer asks for thumbs at once and a thumbs down asks why", async ({ page }) => {
  const api = new FakeMediaWidgetApi();
  speaks(api, "ka", "ltr", "ქართული");
  api.nextAnswerInvitesRating = true;
  await serveSite(page.context(), api, { dataOpen: true });
  await page.goto(`${SITE}/`);
  await expect(chat(page).getByRole("button", { name: "ფოტოს მიმაგრება" })).toBeVisible();

  await ask(page, "მაგიდა ორზე ხვალ რვაზე");
  await expect(chat(page).getByText("გამოგადგათ ეს პასუხი?")).toBeVisible();
  await chat(page).getByRole("button", { name: "არ გამომადგა" }).click();
  await expect(chat(page).getByText("რა იყო არასწორად?")).toBeVisible();
  await chat(page).getByRole("button", { name: "არასწორი ინფორმაცია" }).click();

  await expect(chat(page).getByText("გმადლობთ შეფასებისთვის!")).toBeVisible();
  const answerId = api.messages.find((message) => message.author === "assistant")?.id;
  expect(api.ratings.map(({ rating, reason, message_id }) => [rating, reason, message_id])).toEqual([
    ["bad", undefined, answerId],
    ["bad", "wrong_info", answerId],
  ]);

  // Rated once: the thumbs do not come back on the next page.
  await page.goto(`${SITE}/next`);
  await expect(chat(page).getByText(`Answer to მაგიდა ორზე ხვალ რვაზე`)).toBeVisible();
  await expect(chat(page).getByText("გამოგადგათ ეს პასუხი?")).toBeHidden();
});

test("in Hebrew the thumbs show after two quiet minutes, right to left", async ({ page }) => {
  const api = new FakeMediaWidgetApi();
  speaks(api, "he", "rtl", "עברית");
  await page.clock.install();
  await serveSite(page.context(), api, { dataOpen: true });
  await page.goto(`${SITE}/`);
  await expect(chat(page).getByRole("button", { name: "צירוף תמונה" })).toBeVisible();
  await expect(page.locator(".aw")).toHaveAttribute("dir", "rtl");

  await ask(page, "יש חניה?");
  await expect(chat(page).getByText("Answer to יש חניה?")).toBeVisible();
  const question = chat(page).getByText("התשובה עזרה לכם?");
  await expect(question).toBeHidden();

  await page.clock.fastForward(121_000);
  await expect(question).toBeVisible();
  await chat(page).getByRole("button", { name: "עזר", exact: true }).click();

  await expect(chat(page).getByText("תודה על המשוב!")).toBeVisible();
  expect(api.ratings.map(({ rating, reason }) => [rating, reason])).toEqual([["good", undefined]]);
});

/**
 * A microphone for the page: a steady tone from Web Audio stands in for
 * getUserMedia, so the browser's own MediaRecorder records it (no device
 * or permission prompt in a headless run).
 */
async function lendMicrophone(page: Page): Promise<void> {
  await page.addInitScript(() => {
    if (!navigator.mediaDevices) {
      return;
    }
    navigator.mediaDevices.getUserMedia = async () => {
      const context = new AudioContext();
      const tone = context.createOscillator();
      const output = context.createMediaStreamDestination();
      tone.connect(output);
      tone.start();
      return output.stream;
    };
  });
}

test("holding the microphone records a voice message, letting go uploads it", async ({ page }) => {
  const api = new FakeMediaWidgetApi();
  await lendMicrophone(page);
  await serveSite(page.context(), api, { dataOpen: true });
  await page.goto(`${SITE}/`);
  const mic = chat(page).getByRole("button", { name: "Hold to record a voice message" });
  await expect(mic).toBeVisible();

  await mic.hover();
  await page.mouse.down();
  await expect(chat(page).getByText(/Recording… Release to send, slide away to cancel\. 0:01/)).toBeVisible();
  await page.mouse.up();

  await expect(chat(page).locator(".aw-tray").getByText(/Voice message 0:0[1-2]/)).toBeVisible();
  await expect.poll(() => api.uploads.length).toBe(1);
  expect(api.uploads[0]?.contentType).toMatch(/^audio\/(webm|ogg|mp4)/);
  await chat(page).getByRole("button", { name: "Send" }).click();

  await expect(chat(page).locator(".aw-visitor").getByText(/Voice message/)).toBeVisible();
  expect(api.sentAttachments).toHaveLength(1);
});
