/**
 * Everyday editing of a live business, in Russian, English and Georgian:
 * Assistant → Business profile shows six section cards, each opening the
 * tunnel's screen in its edit mode (no step counter, no time estimate, no
 * Save or Continue). The demo restaurant's owner moves Monday's closing
 * time: it saves itself, the banner over the page counts one change that
 * customers do not get yet and its sheet names the opening hours; putting
 * the time back leaves nothing to apply. The old addresses of the six-step
 * profile open the section that edits their step now.
 */

import { signInAsDemoOwner } from "./support/demo";
import { WEB_URL } from "./support/env";
import { expect, test } from "./support/fixtures";
import { en, ka, ru } from "./support/messages";
import {
  cardName,
  firstClosingTime,
  pendingCount,
  pluralText,
  PROFILE_SECTIONS,
  saveState,
  templatePattern,
  type Messages,
} from "./support/profile";

const LANGUAGES: Record<string, Messages> = { ru, en, ka };

for (const [locale, messages] of Object.entries(LANGUAGES)) {
  test(`a new closing time saves itself and waits in the banner (${locale})`, async ({ page, context, request }) => {
    const owner = await signInAsDemoOwner(request);
    await context.addCookies([
      { name: "aw_session", value: owner.token, url: WEB_URL, httpOnly: true, sameSite: "Lax" },
      { name: "aw_locale", value: locale, url: WEB_URL, sameSite: "Lax" },
    ]);
    const before = await pendingCount(request, owner.token, owner.businessId);
    await page.goto(`/b/${owner.businessId}/assistant/profile`);

    // Six cards, one per section, each with a line of what it holds.
    const cards = page.getByRole("list", { name: messages.profileEdit.cardsLabel });
    for (const section of PROFILE_SECTIONS) {
      await expect(cards.getByRole("link", { name: cardName(messages, section) })).toBeVisible();
    }
    await cards.getByRole("link", { name: cardName(messages, "hours") }).click();

    // The tunnel's hours screen as a section of the page: no counter, no way on, no Save.
    await expect(page).toHaveURL(new RegExp(`/b/${owner.businessId}/assistant/profile/hours$`));
    await expect(page.getByRole("heading", { level: 2, name: messages.profileEdit.sections.hours.title })).toBeVisible();
    const main = page.getByRole("main");
    await expect(main.getByText(templatePattern(messages.tunnel.stepOf))).toHaveCount(0);
    await expect(main.getByRole("button", { name: messages.tunnel.continue })).toHaveCount(0);
    await expect(main.getByRole("button", { name: messages.common.save, exact: true })).toHaveCount(0);
    await expect(saveState(page)).toHaveText(messages.profileEdit.status.idle);

    // A new closing time on Monday saves itself.
    const closes = firstClosingTime(page, messages);
    const original = await closes.inputValue();
    const changed = original === "22:30" ? "22:15" : "22:30";
    await closes.fill(changed);
    await expect(saveState(page)).toHaveAttribute("data-save-state", "saved");
    await expect(saveState(page)).toHaveText(messages.profileEdit.status.saved);

    // The banner counts it, and its sheet says what changed.
    const banner = page.getByTestId("pending-changes-banner");
    await expect(banner).toContainText(pluralText(messages.applyChanges.banner.pending, locale, before + 1));
    await banner.getByRole("button", { name: messages.applyChanges.banner.review }).click();
    const sheet = page.getByRole("dialog", { name: messages.applyChanges.sheet.title });
    await expect(sheet.getByText(messages.applyChanges.areas.hours, { exact: true })).toBeVisible();
    await sheet.getByRole("button", { name: messages.applyChanges.sheet.close, exact: true }).first().click();
    await expect(sheet).toBeHidden();

    // Saved for real: the page opened again shows the new time.
    await page.reload();
    await expect(firstClosingTime(page, messages)).toHaveValue(changed);

    // The time put back: customers already have it, nothing is left to apply.
    await firstClosingTime(page, messages).fill(original);
    if (before === 0) {
      await expect(banner).toBeHidden();
    } else {
      await expect(banner).toContainText(pluralText(messages.applyChanges.banner.pending, locale, before));
    }
  });
}

test("the six-step profile's old addresses open the section that edits their step", async ({ page, owner }) => {
  const base = `/b/${owner.businessId}`;
  const moves: [string, string][] = [
    ["/assistant/profile?step=booking_rules", "/assistant/profile/hours"],
    ["/assistant/profile?step=faq_and_handoff", "/assistant/profile/rules"],
    ["/onboarding?step=offer", "/assistant/profile/offer"],
    ["/onboarding?step=contacts_and_hours", "/assistant/profile/hours"],
    ["/onboarding", "/assistant/profile"],
  ];
  for (const [from, to] of moves) {
    await test.step(from, async () => {
      await page.goto(`${base}${from}`);
      await expect(page).toHaveURL(new RegExp(`${base}${to.replace(/[?]/g, "\\?")}$`));
    });
  }
  // A section that does not exist is not found.
  const missing = await page.request.get(`${base}/assistant/profile/payments`);
  expect(missing.status()).toBe(404);
});
