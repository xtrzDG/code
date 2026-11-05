/**
 * Reply speed on the platform admin's client page: how long the demo
 * restaurant's customers waited for the assistant in the last 7 days, over
 * every channel and per channel (median and 95th percentile).
 */

import { signInAsPlatformAdmin } from "./support/admin";
import { signInAsDemoOwner } from "./support/demo";
import { PLATFORM_ADMIN_EMAIL } from "./support/env";
import { expect, signInContext, test } from "./support/fixtures";
import { en } from "./support/messages";

test.describe.configure({ timeout: 120_000 });

test("the platform admin sees how fast the demo restaurant's customers heard back", async ({ browser, request }) => {
  const owner = await signInAsDemoOwner(request);
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 }, reducedMotion: "reduce" });
  await signInContext(context, await signInAsPlatformAdmin(request, PLATFORM_ADMIN_EMAIL));
  const page = await context.newPage();

  await page.goto(`/admin/clients/${owner.businessId}`);
  const card = page.locator("section", { has: page.getByRole("heading", { level: 2, name: en.adminReplySpeed.title }) });
  const fact = (label: string) =>
    card
      .locator("dl > div")
      .filter({ has: page.locator("dt", { hasText: new RegExp(`^${label.replace(/[()]/g, "\\$&")}$`) }) })
      .locator("dd");

  await expect(card).toBeVisible();
  await expect(fact(en.adminReplySpeed.median)).toHaveText(/^\d+(\.\d)? s$/);
  await expect(fact(en.adminReplySpeed.p95)).toHaveText(/^\d+(\.\d)? s$/);
  expect(Number(await fact(en.adminReplySpeed.replies).innerText())).toBeGreaterThan(0);
  const channels = card.getByRole("table", { name: en.adminReplySpeed.tableCaption });
  await expect(channels.getByRole("row")).not.toHaveCount(0);
  await expect(card.getByText(en.adminReplySpeed.empty)).toHaveCount(0);
  await context.close();
});
