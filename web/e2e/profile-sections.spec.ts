/**
 * The section editors of Assistant → Business profile on a business whose
 * assistant exists (the Berlin salon): the niche's usual hours and ready
 * answers are only offered, never saved until the owner takes them; the
 * offer is a compact table where Enter adds a line and lines pasted from a
 * spreadsheet become lines of their own, each saved by itself. Every
 * section passes the accessibility audit and fits a phone in long texts;
 * on a phone a long offer folds into groups, short rows and a search.
 */

import AxeBuilder from "@axe-core/playwright";
import type { APIRequestContext, Page } from "@playwright/test";

import { API_URL } from "./support/env";
import { expect, test, type Owner } from "./support/fixtures";
import { en } from "./support/messages";
import { waitForNetworkQuiet } from "./support/network";
import { findOverflow, usePseudoLocale } from "./support/overflow";
import { PROFILE_SECTIONS, saveState, templatePattern } from "./support/profile";

const offer = en.tunnelOffer.offer;
const compact = en.profileEdit.offer.compact;

/** Lines of the offer straight through the API: name, kind, price in cents, minutes. */
async function addOffer(request: APIRequestContext, owner: Owner, lines: [string, "service" | "package", number, number | null][]) {
  for (const [title, kind, cents, minutes] of lines) {
    const response = await request.post(`${API_URL}/v1/businesses/${owner.businessId}/knowledge`, {
      headers: { authorization: `Bearer ${owner.token}` },
      data: { kind, title, price_minor: cents, currency_code: "EUR", duration_minutes: minutes, is_active: true },
    });
    expect(response.status(), await response.text()).toBe(201);
  }
}

/** The offer table's line `number` (from 1): its name and its price in euros. */
function offerLine(page: Page, number: number) {
  return {
    name: page.getByLabel(`${offer.name} ${number}`, { exact: true }),
    price: page.getByLabel(`${offer.price.replace("{currency}", "EUR")} ${number}`, { exact: true }),
  };
}

/** A line of a list (offer, ready answers) holding `field`: its save mark says "Saved". */
async function expectLineSaved(field: ReturnType<Page["getByLabel"]>): Promise<void> {
  const line = field.page().locator("li", { has: field });
  await expect(line.getByText(offer.rowSaved, { exact: true })).toBeAttached();
}

test("the niche's usual hours and ready answers wait until the owner takes them", async ({ page, owner }) => {
  await page.goto(`/b/${owner.businessId}/assistant/profile/hours`);
  const usual = page.getByText(en.profileEdit.hours.suggestedTitle);
  await expect(usual).toBeVisible();
  await expect(page.getByRole("checkbox", { name: "Monday" })).toBeChecked();

  // Shown, not saved: the page opened again still offers them.
  await page.reload();
  await expect(usual).toBeVisible();

  // Taken as they are: saved at once, and no longer a suggestion.
  await page.getByRole("button", { name: en.profileEdit.hours.useSuggested }).click();
  await expect(saveState(page)).toHaveAttribute("data-save-state", "saved");
  await expect(usual).toBeHidden();
  await page.reload();
  await expect(page.getByRole("checkbox", { name: "Monday" })).toBeChecked();
  await expect(usual).toBeHidden();

  // Ready answers: the niche's frequent questions are chips, nothing is saved before one is taken.
  await page.goto(`/b/${owner.businessId}/assistant/profile/rules`);
  const answers = page.getByRole("region", { name: en.profileEdit.rules.faqTitle });
  await expect(answers.getByText(en.profileEdit.rules.faqEmpty)).toBeVisible();
  await page.reload();
  await expect(answers.getByText(en.profileEdit.rules.faqEmpty)).toBeVisible();

  const chip = answers
    .getByRole("button", { name: templatePattern(en.profileEdit.rules.addWithAnswer) })
    .or(answers.getByRole("button", { name: templatePattern(en.profileEdit.rules.writeAnswer) }))
    .first();
  const question = ((await chip.textContent()) ?? "").trim();
  await chip.click();
  const questionField = page.getByLabel(en.profileEdit.rules.questionOf.replace("{number}", "1"), { exact: true });
  const answerField = page.getByLabel(en.profileEdit.rules.answerOf.replace("{number}", "1"), { exact: true });
  await expect(questionField).toHaveValue(question);
  // Taken with the niche's answer, or with the owner's own; then changed in place.
  if ((await answerField.inputValue()).trim() === "") {
    await answerField.fill("Yes, any day we are open.");
    await questionField.focus();
  }
  await expectLineSaved(questionField);
  // A change to a saved answer saves itself a moment after the typing stops.
  const edited = `${(await answerField.inputValue()).trim()} Ask us about it.`;
  const patched = page.waitForResponse((response) => response.request().method() === "PATCH" && /\/knowledge\/[^/?]+$/.test(new URL(response.url()).pathname));
  await answerField.fill(edited);
  expect((await patched).ok()).toBe(true);
  await expect(saveState(page)).toHaveAttribute("data-save-state", "saved");

  await page.reload();
  await expect(questionField).toHaveValue(question);
  await expect(answerField).toHaveValue(edited);
});

test("the offer table: Enter adds a line, a spreadsheet's lines are pasted, each saves itself", async ({ page, owner }) => {
  await page.goto(`/b/${owner.businessId}/assistant/profile/offer`);
  await expect(page.getByRole("tab", { name: offer.sources.website })).toBeVisible();
  await expect(page.getByRole("tab", { name: offer.sources.menu })).toBeVisible();

  // The niche's examples wait for prices; a new line is added after them.
  const table = page.getByRole("list", { name: offer.tableLabel });
  await expect(table.getByText(offer.suggestion).first()).toBeVisible();
  const examples = await table.locator("input[data-offer-name]").count();
  await page.getByRole("button", { name: offer.addRow }).click();
  const typed = offerLine(page, examples + 1);
  await expect(typed.name).toBeFocused();
  await typed.name.fill("Beard trim");
  await typed.price.fill("25");

  // Enter in the last line opens the next one; the line left behind saves itself.
  await typed.price.press("Enter");
  const next = offerLine(page, examples + 2);
  await expect(next.name).toBeFocused();
  await expectLineSaved(typed.name);

  // Two lines from a spreadsheet, pasted into the empty line: name, price, minutes.
  await next.name.evaluate((input) => {
    const data = new DataTransfer();
    data.setData("text/plain", "Balayage\t120\t150\nKids haircut\t18\t30\n");
    input.dispatchEvent(new ClipboardEvent("paste", { clipboardData: data, bubbles: true, cancelable: true }));
  });
  await expect(page.getByText(en.profileEdit.offer.pasted.other.replace("{count}", "2"))).toBeVisible();
  await expect(offerLine(page, examples + 2).name).toHaveValue("Balayage");
  await expect(offerLine(page, examples + 3).name).toHaveValue("Kids haircut");
  await expect(page.getByLabel(en.profileEdit.offer.durationOf.replace("{name}", "Balayage"))).toHaveValue("150");
  await expectLineSaved(offerLine(page, examples + 3).name);
  await expect(saveState(page)).toHaveAttribute("data-save-state", "saved");

  // Saved for real: the page opened again holds the owner's three lines (the examples are gone).
  await page.reload();
  await expect(table.locator("input[data-offer-name]")).toHaveCount(3);
  const names = await table.locator("input[data-offer-name]").evaluateAll((inputs) => inputs.map((input) => (input as HTMLInputElement).value));
  expect(names.sort()).toEqual(["Balayage", "Beard trim", "Kids haircut"]);
});

test("every section passes the accessibility audit", async ({ page, owner }) => {
  test.setTimeout(180_000);
  for (const path of ["", ...PROFILE_SECTIONS.map((section) => `/${section}`)]) {
    await test.step(path || "cards", async () => {
      await page.goto(`/b/${owner.businessId}/assistant/profile${path}`);
      await expect(page.getByRole("heading", { level: 1 }).first()).toBeVisible();
      await waitForNetworkQuiet(page);
      const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze();
      const serious = results.violations
        .filter((violation) => violation.impact === "serious" || violation.impact === "critical")
        .map((violation) => `${violation.id}: ${violation.nodes.map((node) => node.target.join(" ")).join(" | ")}`);
      expect(serious, path).toEqual([]);
    });
  }
});

test.describe("on a phone", () => {
  test.use({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });

  test("a long offer folds into groups and short rows, found by name, edited one at a time", async ({ page, request, owner }) => {
    const services = ["Haircut", "Beard trim", "Balayage", "Kids haircut", "Blow-dry", "Manicure", "Pedicure", "Brow shaping", "Hair colouring"];
    await addOffer(request, owner, [
      ...services.map((name, index): [string, "service", number, number] => [name, "service", 2000 + index * 500, 30 + index * 5]),
      ["Bridal look", "package", 30000, null],
      ["Spa day", "package", 12000, null],
    ]);
    await page.goto(`/b/${owner.businessId}/assistant/profile/offer`);

    const servicesGroup = page.getByRole("button", { name: compact.group.other.replace("{kind}", en.knowledge.kindGroups.service).replace("{count}", "9") });
    await expect(servicesGroup).toHaveAttribute("aria-expanded", "false");
    await expect(page.getByRole("button", { name: compact.group.other.replace("{kind}", en.knowledge.kindGroups.package).replace("{count}", "2") })).toBeVisible();
    await expect(page.locator("input[data-offer-name]")).toHaveCount(0);
    // Eleven lines no longer take four screens.
    expect(await page.evaluate(() => document.documentElement.scrollHeight)).toBeLessThan(844 * 2);

    await servicesGroup.click();
    const list = page.getByRole("list", { name: en.knowledge.kindGroups.service });
    await expect(list.locator("[data-offer-fold]")).toHaveCount(9);
    await expect(list.getByRole("button", { name: /^Balayage/ })).toContainText("30 EUR · 40 min");
    expect(await findOverflow(page), "the folded offer at 390 px").toEqual([]);

    // One line opens for editing; Done saves it and folds it again.
    await list.getByRole("button", { name: /^Balayage/ }).click();
    const price = page.getByLabel(`${offer.price.replace("{currency}", "EUR")} 3`, { exact: true });
    await expect(price).toHaveValue("30");
    await price.fill("35");
    await list.getByRole("button", { name: en.common.done }).click();
    await expect(list.getByRole("button", { name: /^Balayage/ })).toContainText("35 EUR · 40 min");
    await expect(saveState(page)).toHaveAttribute("data-save-state", "saved");

    // The search looks through every group, case aside.
    await page.getByRole("searchbox", { name: compact.search }).fill("HAIR");
    await expect(page.locator("[data-offer-fold]")).toHaveCount(3);
    await page.getByRole("searchbox", { name: compact.search }).fill("massage");
    await expect(page.getByText(compact.noMatches.replace("{query}", "massage"))).toBeVisible();

    // Saved for real: the page opened again shows the new price.
    await page.reload();
    await page.getByRole("button", { name: new RegExp(`^${en.knowledge.kindGroups.service}`) }).click();
    await expect(page.getByRole("button", { name: /^Balayage/ })).toContainText("35 EUR");
  });

  test("the cards and every section fit the screen in long texts", async ({ page, context, owner }) => {
    test.setTimeout(180_000);
    await usePseudoLocale(context);
    for (const path of ["", ...PROFILE_SECTIONS.map((section) => `/${section}`)]) {
      await test.step(path || "cards", async () => {
        await page.goto(`/b/${owner.businessId}/assistant/profile${path}`);
        await expect(page.getByRole("heading", { level: 1 })).toHaveText(/^\[.*\]$/);
        await waitForNetworkQuiet(page);
        expect(await findOverflow(page), `${path || "cards"} at 390 px`).toEqual([]);
      });
    }
  });
});
