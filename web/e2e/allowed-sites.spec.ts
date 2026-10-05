/**
 * Channels → Website chat → the websites allowed to show the chat, against
 * the real API: the owner lists the business's own site in the cabinet,
 * and the widget API then refuses a page of another site while it still
 * serves the listed site (with or without "www.") and requests that name
 * no page. Emptying the list lets any site show the chat again.
 */

import type { APIRequestContext } from "@playwright/test";

import { API_URL } from "./support/env";
import { expect, test } from "./support/fixtures";
import { openChatBusiness } from "./support/hosted-chat";
import { en } from "./support/messages";

/** The website chat's embed code needs APP_BASE_URL, which the suite's API does not set. */
const SNIPPET_UNAVAILABLE = /status of 502 \(Bad Gateway\).*\/channels\/web\/snippet/;

/** The status of the widget's config as a page of `origin` loads it (no Origin: a script). */
async function configStatus(request: APIRequestContext, businessId: string, origin?: string): Promise<number> {
  const response = await request.get(`${API_URL}/v1/widget/${businessId}/config`, {
    headers: origin ? { origin } : {},
  });
  return response.status();
}

test("an owner keeps the website chat to their own website", async ({ page, request, account, consoleErrors }) => {
  consoleErrors.allow(SNIPPET_UNAVAILABLE);
  const business = await openChatBusiness(request, account.token);
  expect(await configStatus(request, business.id, "https://copycat.example")).toBe(200);

  await page.goto(`/b/${business.id}/assistant/channels`);
  const card = page.getByRole("region", { name: en.widgetSites.title });
  await expect(card.getByText(en.widgetSites.anySite)).toBeVisible();

  const address = card.getByLabel(en.widgetSites.addLabel);
  await address.fill("not a site");
  await card.getByRole("button", { name: en.widgetSites.add, exact: true }).click();
  await expect(card.getByText(en.widgetSites.invalid)).toBeVisible();

  await address.fill("cafe-batumi.example/menu");
  await address.press("Enter");
  await expect(card.getByRole("list", { name: en.widgetSites.listLabel })).toContainText("cafe-batumi.example");
  await address.fill("www.cafe-batumi.example");
  await address.press("Enter");
  await expect(card.getByText(en.widgetSites.duplicate)).toBeVisible();

  await card.getByRole("button", { name: en.widgetSites.save }).click();
  await expect(page.getByText(en.widgetSites.savedToast)).toBeVisible();
  await expect(card.getByText(en.widgetSites.sites.one.replace("{count}", "1"))).toBeVisible();

  expect(await configStatus(request, business.id, "https://copycat.example")).toBe(403);
  expect(await configStatus(request, business.id, "https://cafe-batumi.example")).toBe(200);
  expect(await configStatus(request, business.id, "http://www.cafe-batumi.example")).toBe(200);
  expect(await configStatus(request, business.id)).toBe(200);

  // Emptying the list: any website again.
  await card.getByRole("button", { name: en.widgetSites.remove.replace("{site}", "cafe-batumi.example") }).click();
  await card.getByRole("button", { name: en.widgetSites.save }).click();
  await expect(page.getByText(en.widgetSites.clearedToast)).toBeVisible();
  await expect(card.getByText(en.widgetSites.anySite)).toBeVisible();
  expect(await configStatus(request, business.id, "https://copycat.example")).toBe(200);
});
