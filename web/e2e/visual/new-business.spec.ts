/**
 * The review gate's brand-new business: an owner signs up, goes through
 * "Create an AI assistant" (support/tunnel.ts walks it in English) and
 * launches for real; then the tunnel's finale in every theme and language at
 * 1440 and 390 px, and the day-0 Overview and the first Inbox at 1440 px
 * dark and 390 px light, in Italian.
 *
 * The launch runs every automatic check on the rehearsal model
 * (LLM_PROVIDER=scripted), whose judge finds answers to improve: the launch
 * screen says so ("Almost there"), and the platform admin publishes the
 * checked version anyway (`accept_failed_tests`, as support does for an
 * owner), so the business is truly live from its finale on.
 *
 * The owner's address is the same every run (it is on screen). Times the
 * run itself made (the launch's minute) are masked: they depend on how long
 * the run took to get here, not on the cabinet.
 */

import type { APIRequestContext, Page } from "@playwright/test";

import { signInAsPlatformAdmin } from "../support/admin";
import { signInByEmail } from "../support/api";
import { API_URL, PLATFORM_ADMIN_EMAIL } from "../support/env";
import { signInContext } from "../support/fixtures";
import { en } from "../support/messages";
import {
  answerBusiness,
  answerChannels,
  answerHours,
  answerOffer,
  answerPeople,
  answerPlace,
  answerTry,
  expectStep,
} from "../support/tunnel";
import { PHONE } from "./clock";
import { expect, matrix, shoot, test, type Shot, type Theme } from "./shots";

const OWNER_EMAIL = "owner@new-business.visual.example";
const BUSINESS_NAME = "Salon Aurora";

/** Clock times on the new business's pages are the run's own. */
const runTimes = (page: Page) => [page.getByText(/\b\d{1,2}:\d{2}\b/)];

/** The new business, once the first test has launched it. */
let launched: { token: string; businessId: string } | undefined;

test.describe.configure({ mode: "serial" });

function shotsOf(businessId: string, theme: Theme): Shot[] {
  const business = `/b/${businessId}`;
  return [
    ...matrix({ name: "new-business-finale", path: `${business}/setup?step=done`, mask: runTimes }),
    { name: "new-business-overview", path: `${business}/overview`, theme, locale: "it", mask: runTimes },
    { name: "new-business-inbox", path: `${business}/inbox`, theme, locale: "it", mask: runTimes },
  ];
}

/** Step 8 for real: the agreement and the launch, until it is live or the checks ask for attention. */
async function launchForReal(page: Page): Promise<"live" | "attention"> {
  await expectStep(page, en.tunnelLaunch.launch.title);
  await page.getByRole("checkbox", { name: en.tunnelLaunch.launch.agreement }).check();
  await page.getByRole("button", { name: en.tunnelLaunch.launch.start }).click();
  const attention = page.getByText(en.tunnelLaunch.launch.attentionTitle);
  await expect(attention.or(page.getByRole("heading", { level: 1, name: en.tunnelLaunch.finale.title }))).toBeVisible({
    timeout: 120_000,
  });
  return (await attention.isVisible()) ? "attention" : "live";
}

/** The platform admin publishes the business's newest version although the rehearsal model's checks failed. */
async function publishAnyway(request: APIRequestContext, owner: string, businessId: string): Promise<void> {
  const versions = await request.get(`${API_URL}/v1/businesses/${businessId}/assistant-versions`, {
    headers: { authorization: `Bearer ${owner}` },
  });
  expect(versions.ok(), await versions.text()).toBe(true);
  const listed = (await versions.json()) as { id: string; created_at: number }[];
  const newest = listed.reduce((latest, version) => (version.created_at > latest.created_at ? version : latest));
  // The owner lets support change things for an hour; support opens the
  // cabinet with a reason, publishes, and both close the door again.
  const writeAccess = (isAllowed: boolean) =>
    request.put(`${API_URL}/v1/businesses/${businessId}/support-access/write-access`, {
      headers: { authorization: `Bearer ${owner}` },
      data: isAllowed ? { is_allowed: true, hours: 1 } : { is_allowed: false },
    });
  const allowed = await writeAccess(true);
  expect(allowed.ok(), await allowed.text()).toBe(true);
  const headers = { authorization: `Bearer ${await signInAsPlatformAdmin(request, PLATFORM_ADMIN_EMAIL)}` };
  const opened = await request.post(`${API_URL}/v1/admin/clients/${businessId}/open`, {
    headers,
    data: { reason: "Publish the first version after the rehearsal checks" },
  });
  expect(opened.ok(), await opened.text()).toBe(true);
  const published = await request.post(`${API_URL}/v1/businesses/${businessId}/assistant-versions/${newest.id}/publish`, {
    headers,
    data: { accept_failed_tests: true },
  });
  expect(published.ok(), await published.text()).toBe(true);
  const closed = await request.delete(`${API_URL}/v1/admin/clients/${businessId}/access`, { headers });
  expect(closed.ok(), await closed.text()).toBe(true);
  const denied = await writeAccess(false);
  expect(denied.ok(), await denied.text()).toBe(true);
}

test("a new business goes from sign-up to a live assistant, at 1440 px", async ({ page, request, context }) => {
  test.setTimeout(300_000);
  const token = await signInByEmail(request, OWNER_EMAIL);
  await signInContext(context, token);
  await page.goto("/businesses");
  await page.waitForURL(/\/create$/);
  await answerBusiness(page, BUSINESS_NAME);
  const businessId = await answerPlace(page);
  await answerOffer(page);
  await answerHours(page);
  await answerPeople(page, OWNER_EMAIL);
  await answerChannels(page);
  await answerTry(page);
  if ((await launchForReal(page)) === "attention") {
    await publishAnyway(request, token, businessId);
  }
  launched = { token, businessId };
  for (const shot of shotsOf(businessId, "dark")) {
    await shoot(page, shot);
  }
});

test.describe("at 390 px", () => {
  test.use(PHONE);

  test("the new business's finale, Overview and Inbox on a phone", async ({ page, context }) => {
    test.setTimeout(150_000);
    expect(launched, "the first test launched the business").toBeDefined();
    await signInContext(context, launched!.token);
    for (const shot of shotsOf(launched!.businessId, "light")) {
      await shoot(page, shot);
    }
  });
});
