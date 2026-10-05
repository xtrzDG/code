/**
 * Staff see what they work with: Overview, Inbox, Bookings, the
 * assistant's test chat and their own notifications in Settings. Owner
 * pages are not in their navigation, and an old link to one says it is for
 * owners instead of failing.
 */

import { inviteStaff, signInByEmail, uniqueEmail } from "./support/api";
import { expect, signInContext, test } from "./support/fixtures";
import { en } from "./support/messages";

test("staff get the test chat and their notifications; owner pages explain themselves", async ({ browser, owner, request }) => {
  const staffEmail = uniqueEmail();
  await inviteStaff(request, owner.token, owner.businessId, staffEmail);
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 }, reducedMotion: "reduce" });
  await signInContext(context, await signInByEmail(request, staffEmail));
  const page = await context.newPage();

  await page.goto(`/b/${owner.businessId}/overview`);
  const navigation = page.getByRole("navigation", { name: en.nav.mainNavigation });
  for (const section of ["overview", "inbox", "bookings", "assistant"] as const) {
    await expect(navigation.getByRole("link", { name: en.navigation.sections[section], exact: true })).toBeVisible();
  }
  // Settings hold only their own notifications (this device, events, quiet hours).
  await navigation.getByRole("link", { name: en.navigation.sections.settings, exact: true }).click();
  await expect(page).toHaveURL(new RegExp(`/b/${owner.businessId}/settings/notifications$`));
  await expect(page.getByRole("region", { name: en.notifications.device.title })).toBeVisible();
  await expect(page.getByRole("button", { name: en.settings.contacts.add })).toHaveCount(0);
  await expect(navigation.getByRole("link", { name: en.navigation.pages.settingsBilling })).toHaveCount(0);

  // The Assistant is its test chat only: no other pages, no tabs, no "Apply changes".
  await navigation.getByRole("link", { name: en.navigation.sections.assistant, exact: true }).click();
  await expect(page).toHaveURL(new RegExp(`/b/${owner.businessId}/assistant$`));
  await expect(navigation.getByRole("link", { name: en.navigation.pages.assistantKnowledge })).toHaveCount(0);
  await expect(page.getByRole("button", { name: en.applyChanges.sheet.apply })).toHaveCount(0);

  for (const path of ["settings/billing", "assistant/knowledge", "assistant/versions"]) {
    await page.goto(`/b/${owner.businessId}/${path}`);
    await expect(page.getByRole("heading", { level: 1, name: en.navigation.ownerOnlyTitle })).toBeVisible();
  }
  await page.getByRole("link", { name: en.navigation.toOverview }).click();
  await expect(page).toHaveURL(new RegExp(`/b/${owner.businessId}/overview$`));
  await context.close();
});
