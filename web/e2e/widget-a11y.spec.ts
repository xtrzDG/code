/**
 * The website chat widget on a host site passes the automated audit
 * (axe-core, WCAG 2.2 A and AA: WCAG_TAGS, no serious or critical
 * violation), closed and open with a conversation, in the light and the
 * dark scheme. Only the widget is audited (the fake host page is not
 * ours); axe reads its open shadow root. The script is the one the real
 * API serves; its API is faked (support/widget-site.ts).
 */

import AxeBuilder from "@axe-core/playwright";
import type { Page } from "@playwright/test";

import { WCAG_TAGS } from "./support/axe";
import { expect, test } from "./support/fixtures";
import { FakeWidgetApi, SITE, ask, chat, loadWidgetSource, serveSite } from "./support/widget-site";

const WIDGET = "[data-assistant-workshop-chat]";

/** Serious and critical violations inside the widget, one line each. */
async function widgetViolations(page: Page): Promise<string[]> {
  const results = await new AxeBuilder({ page }).include(WIDGET).withTags([...WCAG_TAGS]).analyze();
  return results.violations
    .filter((violation) => violation.impact === "serious" || violation.impact === "critical")
    .map((violation) => `${violation.id}: ${violation.nodes.map((node) => node.target.join(" ")).join(" | ")}`);
}

test.beforeAll(async () => {
  await loadWidgetSource();
});

for (const colorScheme of ["light", "dark"] as const) {
  test(`the widget has no serious accessibility violations, closed and open (${colorScheme})`, async ({ page }) => {
    await page.emulateMedia({ colorScheme });
    const api = new FakeWidgetApi();
    await serveSite(page.context(), api);
    await page.goto(`${SITE}/`);

    const launcher = page.getByRole("button", { name: "Open chat" });
    await expect(launcher).toBeVisible();
    expect(await widgetViolations(page), "closed").toEqual([]);

    await launcher.click();
    await expect(chat(page)).toBeVisible();
    await ask(page, "Is the terrace open?");
    await expect(chat(page).getByText("Answer to Is the terrace open?")).toBeVisible();
    expect(await widgetViolations(page), "open, with a conversation").toEqual([]);
  });
}

// The header's text is picked for AA on the business's colour and no more
// (colors.js accentColors): on an accent where white (#767676, 4.54:1) or
// the ink (#828282, 4.57:1) only just reaches it, every line on the header,
// the AI disclosure under the name too, still passes at full strength.
for (const [accent, background, text] of [
  ["#767676", "rgb(118, 118, 118)", "rgb(255, 255, 255)"],
  ["#828282", "rgb(130, 130, 130)", "rgb(26, 24, 22)"],
] as const) {
  test(`the header passes the audit on an accent at the edge of AA (${accent})`, async ({ page }) => {
    const api = new FakeWidgetApi();
    await serveSite(page.context(), api, { attributes: { "data-color": accent } });
    await page.goto(`${SITE}/`);

    await page.getByRole("button", { name: "Open chat" }).click();
    await expect(chat(page)).toBeVisible();
    const header = chat(page).locator(".aw-header");
    await expect(header).toHaveCSS("background-color", background);
    await expect(header.locator(".aw-subtitle")).toHaveCSS("color", text);
    expect(await widgetViolations(page), "open").toEqual([]);
  });
}
