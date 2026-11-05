/**
 * A resource's calendars: the owner opens "Calendars" on a resource, an
 * address inside a network is refused before anything is read, the shared
 * address is shown once and serves an iCal feed, the resource row says its
 * bookings are shared, and Settings → Integrations lists the shared
 * calendar and the resource. No calendar outside the suite is read.
 */

import type { APIRequestContext } from "@playwright/test";

import { API_URL } from "./support/env";
import { expect, test } from "./support/fixtures";
import { en } from "./support/messages";
import { waitForNetworkQuiet } from "./support/network";

test.describe.configure({ timeout: 120_000 });

const RESOURCE = "Studio chair";

async function addResource(request: APIRequestContext, token: string, businessId: string): Promise<void> {
  const response = await request.post(`${API_URL}/v1/businesses/${businessId}/resources`, {
    data: { name: RESOURCE, kind: "staff", capacity: 1 },
    headers: { authorization: `Bearer ${token}` },
  });
  expect(response.status(), await response.text()).toBe(201);
}

test("a resource's calendars: a private address is refused, the shared address serves a feed, Settings lists it", async ({
  page,
  request,
  owner,
  consoleErrors,
}) => {
  // The refused address answers 422, which the browser logs.
  consoleErrors.allow(/status of 422/);
  await addResource(request, owner.token, owner.businessId);

  await page.goto(`/b/${owner.businessId}/assistant/knowledge/resources`);
  await waitForNetworkQuiet(page);
  await page.getByRole("button", { name: en.calendarSync.row.buttonLabel.replace("{name}", RESOURCE) }).click();
  const sheet = page.getByRole("dialog", { name: en.calendarSync.sheet.title.replace("{name}", RESOURCE) });
  await expect(sheet.getByText(en.calendarSync.ical.empty)).toBeVisible();
  await expect(sheet.getByText(en.calendarSync.busy.empty)).toBeVisible();

  // An address inside a network is never read.
  await sheet.getByLabel(en.calendarSync.ical.address).fill("https://127.0.0.1/calendar.ics");
  await sheet.getByRole("button", { name: en.calendarSync.ical.import }).click();
  await expect(page.getByText(en.calendarSync.refusals.address_refused)).toBeVisible();
  await expect(sheet.getByText(en.calendarSync.ical.empty)).toBeVisible();

  // The shared address: shown once, and it serves the resource's busy times as iCal.
  await sheet.getByRole("button", { name: en.calendarSync.export.create }).click();
  await expect(sheet.getByText(en.calendarSync.export.shownOnce)).toBeVisible();
  const address = await sheet.getByRole("textbox", { name: en.calendarSync.export.copy }).inputValue();
  expect(address).toMatch(/\/v1\/public\/ical\/[^/]+\.ics$/);
  const feed = await request.get(address);
  expect(feed.status()).toBe(200);
  expect(feed.headers()["content-type"]).toContain("text/calendar");
  expect(await feed.text()).toContain("BEGIN:VCALENDAR");
  await expect(sheet.getByText(en.calendarSync.export.neverRead)).toBeVisible();

  // The sheet's own close button (the toasts shown over it have one too).
  await sheet.locator("header").getByRole("button", { name: en.common.close }).click();
  await expect(page.getByText(en.calendarSync.row.shared)).toBeVisible();

  // Settings → Integrations: the shared calendar is on, and the resource is listed.
  await page.goto(`/b/${owner.businessId}/settings/integrations`);
  const shared = page.getByRole("listitem").filter({ hasText: en.calendarSync.integrations.kinds.ical_export });
  await expect(shared.getByText(en.calendarSync.integrations.states.on, { exact: true })).toBeVisible();
  await expect(page.getByText(RESOURCE)).toBeVisible();
  await expect(page.getByRole("link", { name: en.calendarSync.integrations.manage })).toHaveAttribute(
    "href",
    `/b/${owner.businessId}/assistant/knowledge/resources`,
  );
});
