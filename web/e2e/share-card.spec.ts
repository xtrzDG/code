/**
 * Channels → Share against the real API: the chat page's link tagged with
 * where it goes, a QR code that really opens that link (the downloaded PNG
 * is read back with a QR decoder), the SVG file, the printable table card
 * and a new address that keeps the old one working.
 */

import { readFile } from "node:fs/promises";

import jsQR from "jsqr";
import type { Download, Page } from "@playwright/test";

import { uniqueSuffix } from "./support/api";
import { WEB_URL } from "./support/env";
import { expect, test } from "./support/fixtures";
import { openChatBusiness } from "./support/hosted-chat";
import { en } from "./support/messages";

/** The QR code in a downloaded PNG, read the way a phone camera would (4 pixels per module). */
async function readQrPng(page: Page, download: Download): Promise<string | null> {
  const base64 = (await readFile((await download.path()) as string)).toString("base64");
  const image = await page.evaluate(async (data) => {
    // Not fetch(data:): the cabinet's policy allows no such request.
    const bytes = Uint8Array.from(atob(data), (character) => character.charCodeAt(0));
    const bitmap = await createImageBitmap(new Blob([bytes], { type: "image/png" }));
    const side = Math.round(bitmap.width / 4);
    const canvas = new OffscreenCanvas(side, side);
    const context = canvas.getContext("2d") as OffscreenCanvasRenderingContext2D;
    context.imageSmoothingEnabled = false;
    context.drawImage(bitmap, 0, 0, side, side);
    return { side, pixels: Array.from(context.getImageData(0, 0, side, side).data) };
  }, base64);
  return jsQR(Uint8ClampedArray.from(image.pixels), image.side, image.side)?.data ?? null;
}

/** The website chat's embed code needs APP_BASE_URL, which the suite's API does not set. */
const SNIPPET_UNAVAILABLE = /status of 502 \(Bad Gateway\).*\/channels\/web\/snippet/;

test("the Share card gives a tagged chat page link whose QR code, files and table card open it", async ({
  page,
  request,
  account,
  consoleErrors,
}) => {
  consoleErrors.allow(SNIPPET_UNAVAILABLE);
  const business = await openChatBusiness(request, account.token);
  await page.goto(`/b/${business.id}/assistant/channels`);
  const share = page.getByRole("region", { name: en.share.title });
  await expect(share.getByTestId("share-chat-page-url")).toHaveText(`${new URL(WEB_URL).host}/c/${business.slug}`);

  await share.getByLabel(en.share.sourceLabel).selectOption("table");

  const tagged = `${WEB_URL}/c/${business.slug}?src=table`;
  await expect(share.getByTestId("share-qr")).toHaveAttribute("data-qr-text", tagged);
  const [png] = await Promise.all([
    page.waitForEvent("download"),
    share.getByRole("button", { name: en.share.downloadLabel.replace("{format}", "PNG") }).click(),
  ]);
  expect(png.suggestedFilename()).toBe(`chat-${business.slug}-table.png`);
  expect(await readQrPng(page, png)).toBe(tagged);

  const [svg] = await Promise.all([
    page.waitForEvent("download"),
    share.getByRole("button", { name: en.share.downloadLabel.replace("{format}", "SVG") }).click(),
  ]);
  const svgText = await readFile((await svg.path()) as string, "utf8");
  expect(svgText).toMatch(/^<svg xmlns="http:\/\/www.w3.org\/2000\/svg"/);
  expect(svgText).toContain(`<title>${new URL(WEB_URL).host}/c/${business.slug}?src=table</title>`);

  const card = page.frameLocator('[data-testid="table-card-preview"]');
  await expect(card.getByRole("heading", { name: business.name })).toBeVisible();
  await expect(card.getByText("Scan to chat with us")).toBeVisible();
  await expect(card.getByText(`${new URL(WEB_URL).host}/c/${business.slug}?src=table`)).toBeVisible();
});

test("a new chat page address is taken at once, and the old one leads to it", async ({
  page,
  request,
  account,
  consoleErrors,
}) => {
  consoleErrors.allow(SNIPPET_UNAVAILABLE);
  const business = await openChatBusiness(request, account.token);
  const address = `shalom-${uniqueSuffix()}`;
  await page.goto(`/b/${business.id}/assistant/channels`);
  const share = page.getByRole("region", { name: en.share.title });

  await share.getByRole("button", { name: en.share.changeAddress }).click();
  await share.getByLabel(en.share.addressLabel).fill("no");
  await share.getByRole("button", { name: en.share.saveAddress }).click();
  await expect(share.getByText(en.share.addressInvalid)).toBeVisible();
  await share.getByLabel(en.share.addressLabel).fill(address);
  await share.getByRole("button", { name: en.share.saveAddress }).click();

  await expect(page.getByText(en.share.addressSaved)).toBeVisible();
  await expect(share.getByTestId("share-chat-page-url")).toHaveText(`${new URL(WEB_URL).host}/c/${address}`);
  await page.goto(`/c/${business.slug}?src=flyer`);
  await expect(page).toHaveURL(new RegExp(`/c/${address}\\?src=flyer$`));
  await expect(page.getByRole("heading", { level: 1, name: business.name })).toBeVisible();
});
