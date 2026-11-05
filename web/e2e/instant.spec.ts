/**
 * The cabinet feels instant: going back shows a section's data from the
 * cache (no skeleton, no spinner), and a request's status changes at
 * once, goes back when the API refuses and can be undone for a few seconds.
 */

import type { Page } from "@playwright/test";

import { openCard, serveCard } from "./support/conversation-card";
import { expect, test } from "./support/fixtures";
import { cardWithLead, leadOf, onLeadPatch, type LeadListItem } from "./support/leads";
import { en } from "./support/messages";

const LOADING_REGION = '[role="status"][aria-busy="true"]';

test("going back shows the section's data at once, from the cache", async ({ page, owner }) => {
  await page.goto(`/b/${owner.businessId}/overview`);
  const navigation = page.getByRole("navigation", { name: en.nav.mainNavigation });
  const customerChannels = page.getByRole("heading", { name: en.channels.sectionCustomer });

  // The Assistant's pages open under it in the sidebar.
  await navigation.getByRole("link", { name: en.navigation.sections.assistant, exact: true }).click();
  await navigation.getByRole("link", { name: en.navigation.pages.assistantChannels, exact: true }).click();
  await expect(customerChannels).toBeVisible();
  await navigation.getByRole("link", { name: en.navigation.pages.assistantKnowledge, exact: true }).click();
  await expect(page).toHaveURL(new RegExp(`/b/${owner.businessId}/assistant/knowledge$`));
  await expect(customerChannels).toBeHidden();

  // From here on the channels never answer: only the cache can show them.
  await page.route(`**/api/backend/v1/businesses/${owner.businessId}/channels`, () => new Promise<void>(() => undefined));
  await page.goBack();
  await expect(page).toHaveURL(new RegExp(`/b/${owner.businessId}/assistant/channels$`));
  await expect(customerChannels).toBeVisible({ timeout: 1_500 });
  await expect(page.locator(LOADING_REGION)).toHaveCount(0);
  await expect(page.getByRole("status").filter({ hasText: en.common.loading })).toHaveCount(0);
  await page.unrouteAll({ behavior: "ignoreErrors" });
});

test.describe("a request's status on its conversation", () => {
  const statusSelect = (page: Page) => page.getByRole("combobox", { name: en.inboxCard.work.requestStatus });

  test("changes at once and goes back when the API refuses", async ({ page, owner, consoleErrors }) => {
    consoleErrors.allow(/status of 500/);
    await serveCard(page, owner.businessId, cardWithLead(owner.businessId, leadOf(owner.businessId, "new")));
    let release = () => undefined as void;
    const refused = new Promise<void>((resolve) => (release = resolve));
    await onLeadPatch(page, owner.businessId, async (route) => {
      await refused;
      await route.fulfill({ status: 500, json: { error: "internal_error", message: "Database is down." } });
    });

    await openCard(page, owner.businessId);
    const status = statusSelect(page);
    await expect(status).toHaveValue("new");

    await status.selectOption("in_progress");
    // Shown while the API has not answered yet.
    await expect(status).toHaveValue("in_progress");

    release();
    await expect(status).toHaveValue("new");
    await expect(page.getByRole("alert").filter({ hasText: en.errors.codes.internal_error })).toBeVisible();
  });

  test("can be undone for a few seconds after the change", async ({ page, owner }) => {
    let stored: LeadListItem = leadOf(owner.businessId, "new");
    await serveCard(page, owner.businessId, () => cardWithLead(owner.businessId, stored));
    const sent: unknown[] = [];
    await onLeadPatch(page, owner.businessId, async (route) => {
      const body = route.request().postDataJSON() as { status: LeadListItem["status"] };
      sent.push(body);
      stored = { ...stored, status: body.status };
      await route.fulfill({ json: stored });
    });

    await openCard(page, owner.businessId);
    await statusSelect(page).selectOption("lost");
    // A lost request is no longer work: it leaves the strip above the transcript.
    await expect(statusSelect(page)).toHaveCount(0);
    const toast = page.getByRole("status").filter({ hasText: en.inboxCard.request.updated.replace("{status}", en.leads.status.lost) });
    await expect(toast).toBeVisible();

    await toast.getByRole("button", { name: en.common.undo }).click();
    await expect(statusSelect(page)).toHaveValue("new");
    await expect.poll(() => sent).toEqual([{ status: "lost" }, { status: "new" }]);
    await expect(page.getByRole("button", { name: en.common.undo })).toHaveCount(0);
  });
});
