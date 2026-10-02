import type { Locator, Page } from "@playwright/test";

import { expect, test } from "./support/fixtures";
import { en } from "./support/messages";

/** "6 required items are missing" → 6; 0 when nothing required is missing. */
async function requiredMissing(summary: Locator): Promise<number> {
  const text = await summary.innerText();
  return text.includes(en.onboarding.gaps.readyTitle) ? 0 : Number(/(\d+)/.exec(text)?.[1] ?? 0);
}

async function saveAndContinue(page: Page, nextStep: string): Promise<void> {
  await page.getByRole("button", { name: en.onboarding.saveAndContinue }).click();
  await expect(page).toHaveURL(new RegExp(`[?&]step=${nextStep}(&|$)`));
}

test("walks the six profile steps of a hair salon in Berlin", async ({ page, newOwner }) => {
  await page.goto(`/b/${newOwner.businessId}/onboarding`);
  await expect(page.getByRole("heading", { level: 1, name: en.onboarding.title })).toBeVisible();
  const stepButtons = page.getByRole("navigation", { name: en.onboarding.stepsLabel }).getByRole("button");
  await expect(stepButtons).toHaveCount(6);
  const summary = page.getByRole("region", { name: en.onboarding.gaps.title });
  await expect(summary).toContainText(/\d/);
  const missingAtStart = await requiredMissing(summary);
  expect(missingAtStart).toBeGreaterThan(0);

  // 1. Niche and languages: the niche's required question.
  await expect(page.getByText("Deutsch ★")).toBeVisible();
  await page.getByRole("checkbox", { name: "Hair" }).check();
  await saveAndContinue(page, "contacts_and_hours");
  await expect(page.getByText(en.onboarding.savedStep).first()).toBeVisible();

  // 2. Contacts and hours: German numbers in national format, Monday copied to every day.
  await page.getByLabel(en.onboarding.contacts.address, { exact: true }).fill("Torstraße 1, 10119 Berlin");
  await page.getByLabel(en.onboarding.contacts.publicPhone).fill("030 12345678");
  await page.getByLabel(en.onboarding.contacts.handoffPhone).fill("0151 23456780");
  await page.getByRole("checkbox", { name: "Monday" }).check();
  await page.getByRole("button", { name: en.onboarding.contacts.copyToAll }).click();
  await expect(page.getByRole("checkbox", { name: "Sunday" })).toBeChecked();

  // Leaving with unsaved changes asks first; dismissing keeps the step.
  page.once("dialog", (dialog) => void dialog.dismiss());
  await stepButtons.nth(2).click();
  await expect(page).not.toHaveURL(/step=offer/);
  await expect(page.getByText(en.onboarding.unsaved)).toBeVisible();
  await saveAndContinue(page, "offer");

  // 3. What you sell: nothing required.
  await saveAndContinue(page, "booking_rules");

  // 4. Booking rules: party size and one specialist to book.
  await page.getByLabel(en.onboarding.booking.maxPartySize).fill("1");
  await page.getByLabel(en.onboarding.resources.name, { exact: true }).fill("Anna");
  await page.getByLabel(en.onboarding.resources.capacity).fill("1");
  await page.getByRole("button", { name: en.onboarding.resources.add, exact: true }).click();
  await expect(page.getByText("Anna", { exact: true })).toBeVisible();
  await saveAndContinue(page, "faq_and_handoff");

  // 5. Questions and handoff, 6. channels: saved as they are.
  await saveAndContinue(page, "channels");
  await page.getByRole("button", { name: en.onboarding.save, exact: true }).click();
  await expect(page.getByText(en.onboarding.savedStep).first()).toBeVisible();

  // Contacts may still miss a manager contact (set in Settings), so not checked here.
  for (const index of [0, 3]) {
    await expect(stepButtons.nth(index)).toContainText(en.onboarding.complete);
  }
  await expect.poll(() => requiredMissing(summary)).toBeLessThan(missingAtStart);

  // The open step is in the address and survives a reload.
  await page.reload();
  await expect(page).toHaveURL(/[?&]step=channels$/);
  await expect(stepButtons.nth(5)).toHaveAttribute("aria-current", "step");

  // The full "what to add" list opens in a side panel; an item opens its step.
  await page.getByRole("button", { name: en.onboarding.gaps.showList }).click();
  const drawer = page.getByRole("dialog", { name: en.onboarding.gaps.title });
  await expect(drawer).toBeVisible();
  await drawer.getByRole("listitem").first().getByRole("button").click();
  await expect(drawer).toBeHidden();
  await expect(page).not.toHaveURL(/step=channels/);
});
