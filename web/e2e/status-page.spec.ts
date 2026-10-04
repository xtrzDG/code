/**
 * The public status page and the platform team's announcements: a platform
 * admin announces an outage of Telegram on the System page; anyone sees it
 * on /status (the overall state, the announcement, Telegram "Not working";
 * the page passes the accessibility audit in that state) and owners see it
 * over their cabinet, unable to hide it; once resolved it
 * leaves the cabinet and the status page lists it under past incidents.
 *
 * The platform's own alerts also set component levels (the suite's fake
 * messengers fail deliveries, which can mark them down), so the spec checks
 * what the announcement decides, not that every other part works.
 */

import AxeBuilder from "@axe-core/playwright";
import type { APIRequestContext } from "@playwright/test";

import { signInAsPlatformAdmin } from "./support/admin";
import { API_URL, STATUS_ADMIN_EMAIL } from "./support/env";
import { expect, signInContext, test } from "./support/fixtures";
import { en } from "./support/messages";
import { waitForNetworkQuiet } from "./support/network";

const texts = en.adminStatus;
const status = en.platformStatus;
const OUTAGE = "Telegram replies are delayed; the team is on it.";

let adminToken: Promise<string> | null = null;

/** One sign-in per test worker: the API sends an address a code at most every 30 seconds. */
function signInAsAdmin(request: APIRequestContext): Promise<string> {
  adminToken ??= signInAsPlatformAdmin(request, STATUS_ADMIN_EMAIL);
  return adminToken;
}

/** Whatever happens in the test, no announcement stays active for the specs after it. */
async function resolveActive(request: APIRequestContext, token: string): Promise<void> {
  const listed = await request.get(`${API_URL}/v1/admin/announcements`, { headers: { Authorization: `Bearer ${token}` } });
  const page = (await listed.json()) as { items: { id: string; status: string }[] };
  for (const item of page.items.filter((announcement) => announcement.status === "active")) {
    await request.patch(`${API_URL}/v1/admin/announcements/${item.id}`, {
      headers: { Authorization: `Bearer ${token}` },
      data: { resolve: true },
    });
  }
}

test("an announced outage shows on the status page and over the cabinet until it is resolved", async ({
  browser,
  request,
  page,
  owner,
}) => {
  const token = await signInAsAdmin(request);
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 }, reducedMotion: "reduce" });
  await signInContext(context, token);
  const admin = await context.newPage();
  try {
    await admin.goto("/admin/system");
    const card = admin.getByRole("region", { name: texts.title });
    await card.getByRole("button", { name: texts.create }).click();
    const dialog = admin.getByRole("dialog", { name: texts.form.createTitle });
    await dialog.getByLabel(texts.form.level).selectOption("outage");
    // A level that is not a notice names the parts it affects.
    await dialog.getByRole("button", { name: texts.form.publish }).click();
    await expect(dialog.getByText(texts.form.errors.componentsRequired)).toBeVisible();
    await expect(dialog.getByText(texts.form.errors.textRequired)).toBeVisible();
    await dialog.getByLabel(status.components.telegram).check();
    await dialog.getByLabel("Text in English").fill(OUTAGE);
    await dialog.getByRole("button", { name: texts.form.publish }).click();
    await expect(dialog).toBeHidden();
    // The closed dialog keeps its form while it fades out: the card's own line.
    await expect(card.getByRole("paragraph").filter({ hasText: OUTAGE })).toBeVisible();

    // Anyone: the status page, without signing in.
    const visitorContext = await browser.newContext({ reducedMotion: "reduce" });
    const visitor = await visitorContext.newPage();
    await visitor.goto("/status");
    await expect(visitor.getByRole("heading", { name: status.overall.outage })).toBeVisible();
    const now = visitor.getByRole("region", { name: status.activeTitle, exact: true });
    await expect(now.getByText(OUTAGE)).toBeVisible();
    await expect(now.getByText(status.affects.replace("{components}", status.components.telegram))).toBeVisible();
    const telegram = visitor.locator("[data-component='telegram']");
    await expect(telegram.getByText(status.levels.outage, { exact: true })).toBeVisible();
    const audit = await new AxeBuilder({ page: visitor }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze();
    expect(audit.violations).toEqual([]);

    // An owner: over every page, and an outage cannot be hidden.
    await page.goto(`/b/${owner.businessId}/bookings`);
    const banner = page.getByRole("region", { name: status.banner.region });
    await expect(banner.getByText(OUTAGE)).toBeVisible();
    await expect(banner.getByRole("button", { name: status.banner.dismiss })).toHaveCount(0);

    // Resolved: the banner leaves, the status page keeps it as a past incident.
    await card.getByRole("button", { name: texts.resolve }).click();
    await admin.getByRole("dialog", { name: texts.resolveTitle }).getByRole("button", { name: texts.resolve }).click();
    await expect(card.getByText(texts.status.resolved, { exact: true })).toBeVisible();

    await page.reload();
    await waitForNetworkQuiet(page);
    await expect(page.getByRole("region", { name: status.banner.region })).toHaveCount(0);
    await visitor.reload();
    await expect(visitor.getByRole("region", { name: status.pastTitle }).getByText(OUTAGE)).toBeVisible();
    await expect(now.getByText(OUTAGE)).toHaveCount(0);
    await visitorContext.close();
  } finally {
    await resolveActive(request, token);
    await context.close();
  }
});

test("an owner hides a notice, and it stays hidden after a reload", async ({ request, page, owner }) => {
  const token = await signInAsAdmin(request);
  try {
    const created = await request.post(`${API_URL}/v1/admin/announcements`, {
      headers: { Authorization: `Bearer ${token}` },
      data: { level: "info", components: [], messages: [{ language: "en", text: "New invoices arrive on the 1st of each month." }] },
    });
    expect(created.status(), await created.text()).toBe(201);

    await page.goto(`/b/${owner.businessId}/bookings`);
    const banner = page.getByRole("region", { name: status.banner.region });
    await expect(banner.getByText("New invoices arrive")).toBeVisible();
    await banner.getByRole("button", { name: status.banner.dismiss }).click();
    await expect(banner).toHaveCount(0);
    await page.reload();
    await waitForNetworkQuiet(page);
    await expect(page.getByRole("region", { name: status.banner.region })).toHaveCount(0);
  } finally {
    await resolveActive(request, token);
  }
});
