/**
 * Settings → General's customer memory: on by default; the owner lets the
 * team's notes reach it and turns it off (the notes switch then waits for
 * the memory), each change saves at once and stays; on a phone the card
 * fits the screen.
 */

import { expect, test } from "./support/fixtures";
import { en } from "./support/messages";

const memory = en.customerMemory;

test("the owner shares the team's notes, turns the memory off and the choice stays", async ({ page, owner }) => {
  await page.goto(`/b/${owner.businessId}/settings`);

  const card = page.getByTestId("customer-memory");
  const remember = card.getByRole("switch", { name: memory.remember.label });
  const notes = card.getByRole("switch", { name: memory.notes.label });
  await expect(remember).toHaveAttribute("aria-checked", "true");
  await expect(notes).toHaveAttribute("aria-checked", "false");
  await expect(card.getByText(memory.remembers.summaries)).toBeVisible();

  await notes.click();
  await expect(page.getByText(memory.notesShared)).toBeVisible();
  await expect(notes).toHaveAttribute("aria-checked", "true");

  await remember.click();
  await expect(page.getByText(memory.turnedOff)).toBeVisible();
  await expect(remember).toHaveAttribute("aria-checked", "false");
  await expect(notes).toBeDisabled();
  await expect(card.getByText(memory.notes.needsMemory)).toBeVisible();

  await page.reload();
  const reloaded = page.getByTestId("customer-memory");
  await expect(reloaded.getByRole("switch", { name: memory.remember.label })).toHaveAttribute("aria-checked", "false");
  await expect(reloaded.getByRole("switch", { name: memory.notes.label })).toBeDisabled();

  await reloaded.getByRole("switch", { name: memory.remember.label }).click();
  await expect(page.getByText(memory.turnedOn)).toBeVisible();
  // The notes choice made before was kept while the memory was off.
  await expect(reloaded.getByRole("switch", { name: memory.notes.label })).toHaveAttribute("aria-checked", "true");
});

test("on a phone the customer memory card fits the screen", async ({ page, owner }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(`/b/${owner.businessId}/settings`);

  await expect(page.getByRole("heading", { name: memory.title })).toBeVisible();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(0);
});
