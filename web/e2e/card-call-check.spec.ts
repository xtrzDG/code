/**
 * The after-call check on the conversation card: a checked call carries a
 * calm label, a call whose assistant mentioned values missing from the
 * business data shows them with what to do next. The card is served by the
 * test (see support/conversation-card.ts); calls only come from the voice
 * platform.
 */

import { expect, test } from "./support/fixtures";
import { en } from "./support/messages";
import { CONVERSATION_ID, cardWithCalls, serveCard } from "./support/conversation-card";

test("a checked call is labelled and one with values missing from the data says what to check", async ({ page, owner }) => {
  const card = cardWithCalls(owner.businessId, ["call_clean", "call_flagged"]);
  card.calls = (card.calls ?? []).map((call, index) =>
    index === 0
      ? { ...call, guard_verdict: "clean", unverified_values: [] }
      : { ...call, outcome: "lead", guard_verdict: "handed_off", unverified_values: ["85 GEL", "21:30"] },
  );
  await serveCard(page, owner.businessId, card);

  await page.goto(`/b/${owner.businessId}/messages/${CONVERSATION_ID}`);

  const guard = en.conversations.calls.guard;
  await expect(page.getByText(guard.clean, { exact: true })).toBeVisible();
  await expect(page.getByText(guard.handedOff, { exact: true })).toBeVisible();
  const warning = page.getByText(guard.handedOffTitle);
  await expect(warning).toBeVisible();
  const values = page.getByRole("list", { name: guard.valuesLabel });
  await expect(values.getByRole("listitem")).toHaveText(["85 GEL", "21:30"]);
  await expect(page.getByText(guard.hint)).toBeVisible();
  // Only the call with findings carries the warning.
  await expect(page.getByText(guard.flaggedTitle, { exact: true })).toHaveCount(0);
});

test("on a phone the findings fit the screen", async ({ page, owner }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  const card = cardWithCalls(owner.businessId, ["call_flagged"]);
  card.calls = (card.calls ?? []).map((call) => ({ ...call, guard_verdict: "flagged", unverified_values: ["50 GEL"] }));
  await serveCard(page, owner.businessId, card);

  await page.goto(`/b/${owner.businessId}/messages/${CONVERSATION_ID}`);

  const title = page.getByText(en.conversations.calls.guard.flaggedTitle, { exact: true });
  await expect(title).toBeVisible();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(0);
});
