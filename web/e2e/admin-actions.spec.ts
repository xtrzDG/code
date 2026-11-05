/**
 * A platform admin acts on a client and keeps its story: grants credit
 * with a reason (the account card shows it and the timeline names the
 * reason), then writes a pinned note for the team. The Metrics page counts
 * every business next to the owners and says how many platform admins it
 * leaves out, with a switch to count them in.
 */

import { signInAsPlatformAdmin } from "./support/admin";
import { signInAsDemoOwner } from "./support/demo";
import { PLATFORM_ADMIN_EMAIL } from "./support/env";
import { expect, signInContext, test } from "./support/fixtures";
import { en } from "./support/messages";

const actions = en.adminActions;
const story = en.adminStory;
const metrics = en.adminMetrics;

const REASON = "Goodwill for the slow setup week";
const NOTE = "Prefers WhatsApp after 18:00";

test("the platform admin grants credit with a reason and pins a note for the team", async ({ browser, request }) => {
  const owner = await signInAsDemoOwner(request);
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 }, reducedMotion: "reduce" });
  await signInContext(context, await signInAsPlatformAdmin(request, PLATFORM_ADMIN_EMAIL));
  const page = await context.newPage();
  await page.goto(`/admin/clients/${owner.businessId}`);

  await page.getByRole("button", { name: actions.menu }).click();
  await page.getByRole("menuitem", { name: actions.credit.action }).click();
  const dialog = page.getByRole("dialog");
  await dialog.getByRole("textbox", { name: /Amount/ }).fill("25");
  await dialog.getByRole("textbox", { name: actions.reasonLabel }).fill(REASON);
  await dialog.getByRole("button", { name: actions.credit.confirm }).click();
  await expect(page.getByText(actions.done)).toBeVisible();
  await expect(dialog).toBeHidden();

  const account = page.getByRole("region", { name: actions.account.title });
  await expect(account.getByText(actions.account.credit)).toBeVisible();
  const timeline = page.getByRole("region", { name: story.timeline.title });
  await expect(timeline.getByText(`Why: ${REASON}`)).toBeVisible();

  const notes = page.getByRole("region", { name: story.notes.title });
  await notes.getByRole("textbox", { name: story.notes.label }).fill(NOTE);
  await notes.getByRole("checkbox", { name: story.notes.pinNew }).check();
  await notes.getByRole("button", { name: story.notes.add }).click();
  await expect(notes.getByText(NOTE)).toBeVisible();
  await expect(notes.getByText(story.notes.pinned, { exact: true })).toBeVisible();
  await context.close();
});

test("the Metrics page counts every business and names the platform admins it leaves out", async ({ browser, request }) => {
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 }, reducedMotion: "reduce" });
  await signInContext(context, await signInAsPlatformAdmin(request, PLATFORM_ADMIN_EMAIL));
  const page = await context.newPage();
  await page.goto("/admin/metrics");

  const businesses = page.getByRole("region", { name: metrics.businesses.title });
  await expect(businesses.getByText(metrics.funnel.steps.went_live, { exact: true })).toBeVisible();
  await expect(page.getByRole("region", { name: metrics.businesses.tunnelTitle })).toBeVisible();
  await expect(page.getByText(metrics.admins.note)).toBeVisible();

  // The admin who just signed up is one of the platform admins left out.
  await page.getByRole("button", { name: metrics.admins.include }).click();
  await expect(page).toHaveURL(/include_admins=true/);
  await expect(page.getByText(metrics.admins.included)).toBeVisible();
  await page.getByRole("button", { name: metrics.admins.exclude }).click();
  await expect(page).toHaveURL(/\/admin\/metrics$/);
  await context.close();
});
