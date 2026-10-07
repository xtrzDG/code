/**
 * Working through the inbox on a laptop (1440×900), against the real API and
 * the demo restaurant (support/demo.ts):
 *
 *  - the All view shows at least eight whole conversations on the first
 *    screen; Compact shows more, and the choice and the list's width (the
 *    edge moves with the arrow keys, Home and End) stay after a reload;
 *  - the keyboard: J moves to a visitor's conversation, E resolves its
 *    handoff, Undo in the message opens it again; ? lists the keys and /
 *    goes to the search;
 *  - X selects two conversations, "Mark resolved" resolves both through the
 *    handoffs' own endpoint, and Undo brings both back.
 *
 * The API is the judge of what happened. The inbox's one-time tip is
 * marked seen first, so it does not take the list's place.
 */

import type { APIRequestContext, Page } from "@playwright/test";

import { uniqueSuffix } from "./support/api";
import { signInAsDemoOwner, visitorAsksForPerson, type DemoOwner } from "./support/demo";
import { API_URL } from "./support/env";
import { expect, signInContext, test } from "./support/fixtures";
import { cardOf, waitingConversationOf } from "./support/inbox";
import { en } from "./support/messages";

test.describe.configure({ timeout: 120_000 });
test.use({ viewport: { width: 1440, height: 900 } });

const triage = en.inboxTriage;

/** The demo owner, with the inbox's tip already seen, signed in on `page`. */
async function demoInbox(page: Page, request: APIRequestContext): Promise<DemoOwner> {
  const owner = await signInAsDemoOwner(request);
  const seen = await request.put(`${API_URL}/v1/me/help/coach-marks/inbox`, { headers: { authorization: `Bearer ${owner.token}` } });
  expect(seen.ok(), await seen.text()).toBe(true);
  await signInContext(page.context(), owner.token);
  return owner;
}

/** The id of the row the keyboard focus is on. */
function focusedRow(page: Page): Promise<string | null> {
  return page.evaluate(() => document.activeElement?.closest("[data-inbox-row]")?.getAttribute("data-inbox-row") ?? null);
}

/** Moves the cursor with J (then K, from the end) until it stands on conversation `id`. */
async function cursorTo(page: Page, id: string): Promise<void> {
  for (const key of ["j", "k"]) {
    let previous: string | null = null;
    for (let step = 0; step < 100; step += 1) {
      await page.keyboard.press(key);
      const now = await focusedRow(page);
      if (now === id) {
        return;
      }
      if (now === previous) {
        break;
      }
      previous = now;
    }
  }
  throw new Error(`the cursor never reached ${id}`);
}

async function isWaiting(request: APIRequestContext, owner: DemoOwner, conversationId: string): Promise<boolean> {
  const card = await cardOf(request, owner.token, owner.businessId, conversationId);
  return card.handoffs.some((handoff) => handoff.status !== "resolved");
}

/** Rows wholly on the first screen. */
function rowsOnScreen(page: Page): Promise<number> {
  return page.evaluate(
    () =>
      [...document.querySelectorAll("[data-inbox-row]")].filter((row) => {
        const box = row.getBoundingClientRect();
        return box.top >= 0 && box.bottom <= window.innerHeight;
      }).length,
  );
}

test("a laptop shows eight conversations or more; Compact and the list's width stay after a reload", async ({ page, request }) => {
  const owner = await demoInbox(page, request);
  await page.goto(`/b/${owner.businessId}/inbox?view=all`);
  await expect(page.locator("[data-inbox-row]").nth(12)).toBeAttached();
  expect(await rowsOnScreen(page), "whole rows on a 1440×900 screen").toBeGreaterThanOrEqual(8);

  const comfortable = await rowsOnScreen(page);
  // The radio itself is visually hidden: people press its label.
  await page.getByTitle(triage.density.compact, { exact: true }).click();
  await expect(page.getByRole("radio", { name: triage.density.compact })).toBeChecked();
  await expect.poll(() => rowsOnScreen(page)).toBeGreaterThan(comfortable);

  const edge = page.getByRole("separator", { name: triage.resize.label });
  await edge.focus();
  await page.keyboard.press("End");
  await expect(edge).toHaveAttribute("aria-valuenow", "520");
  await page.keyboard.press("ArrowLeft");
  await expect(edge).toHaveAttribute("aria-valuenow", "504");
  const list = page.locator("[data-inbox-list]");
  await expect.poll(async () => Math.round((await list.boundingBox())?.width ?? 0)).toBe(504);

  await page.reload();
  await expect(page.getByRole("radio", { name: triage.density.compact })).toBeChecked();
  await expect(page.getByRole("separator", { name: triage.resize.label })).toHaveAttribute("aria-valuenow", "504");
  await expect.poll(async () => Math.round((await list.boundingBox())?.width ?? 0)).toBe(504);
});

test("J moves to a conversation, E resolves it and Undo opens it again; ? lists the keys, / searches", async ({ page, request }) => {
  const owner = await demoInbox(page, request);
  const visitor = await visitorAsksForPerson(request, owner.businessId, `Triage visitor ${uniqueSuffix()}`);
  const conversationId = await waitingConversationOf(request, owner.token, owner.businessId, visitor.name);

  await page.goto(`/b/${owner.businessId}/inbox`);
  const row = page.locator(`[data-inbox-row="${conversationId}"]`);
  await expect(row).toBeVisible();
  await cursorTo(page, conversationId);

  await page.keyboard.press("e");
  const toast = page.getByRole("status").filter({ hasText: triage.resolved.one.replace("{count}", "1") });
  await expect(toast).toBeVisible();
  await expect(row).toHaveCount(0);
  await expect.poll(() => isWaiting(request, owner, conversationId)).toBe(false);

  await toast.getByRole("button", { name: en.common.undo }).click();
  await expect(page.getByRole("status").filter({ hasText: triage.undone })).toBeVisible();
  await expect.poll(() => isWaiting(request, owner, conversationId)).toBe(true);
  await expect(row).toBeVisible();

  await page.locator("h1").click();
  await page.keyboard.press("Shift+?");
  const sheet = page.getByRole("dialog", { name: triage.keys.title });
  await expect(sheet.getByText(triage.keys.actions.resolve)).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(sheet).toBeHidden();
  await page.keyboard.press("/");
  await expect(page.locator("[data-inbox-search]")).toBeFocused();
});

test("X selects two conversations, Mark resolved resolves both and Undo brings both back", async ({ page, request }) => {
  const owner = await demoInbox(page, request);
  const visitors = [
    await visitorAsksForPerson(request, owner.businessId, `Triage pair ${uniqueSuffix()}`),
    await visitorAsksForPerson(request, owner.businessId, `Triage pair ${uniqueSuffix()}`),
  ];
  const ids = await Promise.all(visitors.map((visitor) => waitingConversationOf(request, owner.token, owner.businessId, visitor.name)));

  await page.goto(`/b/${owner.businessId}/inbox`);
  for (const id of ids) {
    await expect(page.locator(`[data-inbox-row="${id}"]`)).toBeVisible();
    await cursorTo(page, id);
    await page.keyboard.press("x");
  }
  await expect(page.getByText(triage.select.count.other.replace("{count}", "2"))).toBeVisible();
  for (const visitor of visitors) {
    await expect(page.getByRole("checkbox", { name: triage.select.row.replace("{name}", visitor.name) })).toBeChecked();
  }

  await page.getByRole("button", { name: triage.select.resolve, exact: true }).click();
  const toast = page.getByRole("status").filter({ hasText: triage.resolved.other.replace("{count}", "2") });
  await expect(toast).toBeVisible();
  for (const id of ids) {
    await expect(page.locator(`[data-inbox-row="${id}"]`)).toHaveCount(0);
    await expect.poll(() => isWaiting(request, owner, id)).toBe(false);
  }

  await toast.getByRole("button", { name: en.common.undo }).click();
  for (const id of ids) {
    await expect.poll(() => isWaiting(request, owner, id)).toBe(true);
    await expect(page.locator(`[data-inbox-row="${id}"]`)).toBeVisible();
  }
});
