/**
 * Steps of "Create an AI assistant" for the tests that walk it: each one
 * answers a screen the way an owner would and moves on, checking the
 * screen's question first. Texts come from the cabinet's dictionaries.
 */

import { expect, type Page } from "@playwright/test";

import { en } from "./messages";

const TUNNEL = /\/b\/([^/]+)\/setup/;

/** The step's question (the screen's only level-1 heading). */
export async function expectStep(page: Page, title: string): Promise<void> {
  await expect(page.getByRole("heading", { level: 1, name: title })).toBeVisible();
}

export async function pressContinue(page: Page): Promise<void> {
  await page.getByRole("button", { name: en.tunnel.continue, exact: true }).click();
}

/** The page is as wide as the screen (nothing scrolls sideways on a phone). */
export async function expectNoSidewaysScroll(page: Page): Promise<void> {
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  expect(overflow).toBeLessThanOrEqual(0);
}

/** Step 1 on /create: a hair salon's name, its kind and the kind's required question. */
export async function answerBusiness(page: Page, name: string): Promise<void> {
  await expectStep(page, en.tunnelBusiness.business.title);
  await page.getByLabel(en.tunnelBusiness.business.name).fill(name);
  await page.locator("label").filter({ hasText: /^Beauty salons/ }).click();
  // The kind asks which services the salon offers: Continue refuses until one is chosen.
  await pressContinue(page);
  await expect(page.getByText(en.validation.required)).toBeVisible();
  await page.getByRole("checkbox", { name: "Hair" }).check();
  await pressContinue(page);
}

/** Step 2 on /create: Germany, Berlin and the salon's address; the business is created. */
export async function answerPlace(page: Page): Promise<string> {
  await expect(page).toHaveURL(/\/create\?step=place$/);
  await expectStep(page, en.tunnelBusiness.place.title);
  await page.getByLabel(en.tunnelBusiness.place.country).selectOption("DE");
  const languages = page.getByRole("group", { name: en.tunnelBusiness.place.languages });
  await expect(languages.getByRole("checkbox", { name: /Deutsch/ })).toBeChecked();
  await page.getByLabel(en.tunnelBusiness.place.city).fill("Berlin");
  // A salon takes bookings, so its address is required.
  await pressContinue(page);
  await expect(page.getByText(en.tunnelBusiness.place.errors.address)).toBeVisible();
  await page.getByLabel(en.tunnelBusiness.place.address).fill("Torstraße 1, 10119 Berlin");
  await pressContinue(page);
  await expect(page).toHaveURL(/\/b\/[^/]+\/setup\?step=offer$/, { timeout: 20_000 });
  return TUNNEL.exec(new URL(page.url()).pathname)?.[1] ?? "";
}

/** Step 3: the first suggested service gets a price; the examples without one are not saved. */
export async function answerOffer(page: Page): Promise<void> {
  await expectStep(page, en.tunnelOffer.offer.title);
  const price = page.getByRole("textbox", { name: `${en.tunnelOffer.offer.price.replace("{currency}", "EUR")} 1` });
  await price.fill("35");
  await price.press("Tab");
  await expect(page.getByText(en.tunnelOffer.offer.priced.one.replace("{count}", "1"))).toBeVisible();
  await pressContinue(page);
  await expect(page).toHaveURL(/step=hours$/);
}

/** Step 4: the niche's usual week and booking rules, accepted as they are. */
export async function answerHours(page: Page): Promise<void> {
  await expectStep(page, en.tunnelOffer.hours.title);
  await expect(page.getByRole("checkbox", { name: "Monday" })).toBeChecked();
  await pressContinue(page);
  await expect(page).toHaveURL(/step=people$/, { timeout: 20_000 });
}

/** Step 5: the owner's own e-mail in one tap. */
export async function answerPeople(page: Page, email: string): Promise<void> {
  await expectStep(page, en.tunnelTeam.people.title);
  // Without a person Continue explains why it cannot go on.
  await pressContinue(page);
  await expect(page.getByText(en.tunnelTeam.people.errors.none)).toBeVisible();
  await page.getByRole("button", { name: new RegExp(`${en.tunnelTeam.people.me} ${en.tunnelTeam.people.by.email}`) }).click();
  const current = page.getByRole("region", { name: en.tunnelTeam.people.current });
  await expect(current.getByText(email)).toBeVisible();
  await pressContinue(page);
  await expect(page).toHaveURL(/step=channels$/);
}

/** Step 6: the website chat, on by default. */
export async function answerChannels(page: Page): Promise<void> {
  await expectStep(page, en.tunnelTeam.channels.title);
  await expect(page.getByRole("switch", { name: en.tunnelTeam.channels.web.toggle })).toHaveAttribute("aria-checked", "true");
  await pressContinue(page);
  await expect(page).toHaveURL(/step=try$/, { timeout: 20_000 });
}

/** Step 7: one suggested question; the API's model passes it to a person here. */
export async function answerTry(page: Page): Promise<void> {
  await expectStep(page, en.tunnelLaunch.try.title);
  await expect(page.getByRole("button", { name: en.tunnel.continue, exact: true })).toBeDisabled();
  await page.getByRole("button", { name: en.tunnelLaunch.try.questions.hours }).click();
  const conversation = page.getByRole("log", { name: en.tunnelLaunch.try.chatLabel });
  await expect(conversation.getByText(`${en.tunnelLaunch.try.assistant}:`, { exact: true })).toHaveCount(1, { timeout: 30_000 });
  await pressContinue(page);
  await expect(page).toHaveURL(/step=launch$/);
}

/**
 * The launch's progress as the API reports it, played by the test: a first
 * launch runs every automatic check, too long for walking the screens
 * (apply-changes.spec.ts runs real checks on the rehearsal model).
 * Building, checking (three checks), publishing, live.
 */
export async function playLaunch(page: Page): Promise<void> {
  let reads = 0;
  const view = (stage: string | null, done = 0) => ({
    business_id: "played",
    stage,
    is_in_progress: stage !== null && stage !== "live",
    has_unapplied_changes: stage !== "live",
    checks_done: done,
    checks_total: 3,
    attention: [],
  });
  await page.route(/\/api\/backend\/v1\/businesses\/[^/]+\/assistant\/apply(\?|$)/, async (route) => {
    if (route.request().method() === "POST") {
      reads = 1;
      await route.fulfill({ status: 202, json: view("building") });
      return;
    }
    if (reads === 0) {
      await route.fulfill({ json: view(null) });
      return;
    }
    reads += 1;
    const stage = reads < 3 ? "building" : reads < 6 ? "checking" : reads < 7 ? "publishing" : "live";
    await route.fulfill({ json: view(stage, Math.min(Math.max(reads - 3, 0), 3)) });
  });
}

/** Step 8: the agreement, the launch and its progress, then the finale. */
export async function launch(page: Page): Promise<void> {
  await expectStep(page, en.tunnelLaunch.launch.title);
  await pressLaunch(page);
  await expect(page.getByText(en.tunnelLaunch.launch.agreementRequired)).toBeVisible();
  await page.getByRole("checkbox", { name: en.tunnelLaunch.launch.agreement }).check();
  await pressLaunch(page);
  await expect(page.getByRole("listitem").filter({ hasText: en.tunnelLaunch.launch.stages.checking })).toBeVisible();
  await expect(page).toHaveURL(/step=done$/, { timeout: 30_000 });
  await expectStep(page, en.tunnelLaunch.finale.title);
}

async function pressLaunch(page: Page): Promise<void> {
  await page.getByRole("button", { name: en.tunnelLaunch.launch.start }).click();
}
