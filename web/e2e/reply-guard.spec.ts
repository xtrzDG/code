/**
 * The reply guard on the platform admin's client page: how many of the
 * demo restaurant's replies of the last 7 days it checked, held back
 * (rewritten once or passed to staff) and how many messages tried to
 * change the assistant's instructions — the verdicts seeding stored on the
 * replies (Lukas Weber's corkage fee passed to staff, a Georgian reply
 * rewritten for an unsupported parking claim), as the inbox shows them.
 */

import { signInAsPlatformAdmin } from "./support/admin";
import { signInAsDemoOwner } from "./support/demo";
import { PLATFORM_ADMIN_EMAIL } from "./support/env";
import { expect, signInContext, test } from "./support/fixtures";
import { en } from "./support/messages";

test.describe.configure({ timeout: 120_000 });

test("the platform admin sees what the reply guard did for the demo restaurant", async ({ browser, request }) => {
  const owner = await signInAsDemoOwner(request);
  const context = await browser.newContext({ viewport: { width: 390, height: 844 }, reducedMotion: "reduce" });
  await signInContext(context, await signInAsPlatformAdmin(request, PLATFORM_ADMIN_EMAIL));
  const page = await context.newPage();

  await page.goto(`/admin/clients/${owner.businessId}`);
  const card = page.locator("section", { has: page.getByRole("heading", { level: 2, name: en.adminReplyGuard.title }) });
  const fact = (label: string) =>
    card
      .locator("dl > div")
      .filter({ has: page.locator("dt", { hasText: new RegExp(`^${label}$`) }) })
      .locator("dd");

  await expect(card).toBeVisible();
  expect(Number(await fact(en.adminReplyGuard.checked).innerText())).toBeGreaterThan(0);
  // Two of the week's checked replies, with their share beside them ("2 4% of replies").
  const share = en.adminReplyGuard.heldBackShare.replace("{share}", "");
  await expect(fact(en.adminReplyGuard.heldBack)).toHaveText(new RegExp(`^2\\s*\\d+%${share}$`));
  await expect(fact(en.adminReplyGuard.rewritten)).toHaveText("1");
  await expect(fact(en.adminReplyGuard.handedOff)).toHaveText("1");
  await expect(fact(en.adminReplyGuard.injectionFlags)).toHaveText("0");
  await expect(card.getByText(en.adminReplyGuard.empty)).toHaveCount(0);
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(0);
  await context.close();
});
