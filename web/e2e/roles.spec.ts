/**
 * Staff see what they work with: Overview, Messages, Bookings and the
 * assistant's test chat. Owner pages are not in their navigation, and an
 * old link to one says it is for owners instead of failing.
 */

import { inviteStaff, signInByEmail, uniqueEmail } from "./support/api";
import { expect, signInContext, test } from "./support/fixtures";
import { en } from "./support/messages";

test("staff get four sections and the test chat; owner pages explain themselves", async ({ browser, owner, request }) => {
  const staffEmail = uniqueEmail();
  await inviteStaff(request, owner.token, owner.businessId, staffEmail);
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 }, reducedMotion: "reduce" });
  await signInContext(context, await signInByEmail(request, staffEmail));
  const page = await context.newPage();

  await page.goto(`/b/${owner.businessId}/overview`);
  const navigation = page.getByRole("navigation", { name: en.nav.mainNavigation });
  for (const section of ["overview", "messages", "bookings", "assistant"] as const) {
    await expect(navigation.getByRole("link", { name: en.navigation.sections[section], exact: true })).toBeVisible();
  }
  await expect(navigation.getByRole("link", { name: en.navigation.sections.settings, exact: true })).toHaveCount(0);

  // The Assistant is its test chat only: no other pages, no tabs, no "Apply changes".
  await navigation.getByRole("link", { name: en.navigation.sections.assistant, exact: true }).click();
  await expect(page).toHaveURL(new RegExp(`/b/${owner.businessId}/assistant$`));
  await expect(navigation.getByRole("link", { name: en.navigation.pages.assistantKnowledge })).toHaveCount(0);
  await expect(page.getByRole("button", { name: en.navigation.applyChanges })).toHaveCount(0);

  for (const path of ["settings/billing", "assistant/knowledge", "assistant/versions"]) {
    await page.goto(`/b/${owner.businessId}/${path}`);
    await expect(page.getByRole("heading", { level: 1, name: en.navigation.ownerOnlyTitle })).toBeVisible();
  }
  await page.getByRole("link", { name: en.navigation.toOverview }).click();
  await expect(page).toHaveURL(new RegExp(`/b/${owner.businessId}/overview$`));
  await context.close();
});
