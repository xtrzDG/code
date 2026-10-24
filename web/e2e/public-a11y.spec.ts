/**
 * The public pages pass the same automated audit as the cabinet (axe-core,
 * WCAG 2.1 A and AA, no serious or critical violation), in both themes.
 */

import AxeBuilder from "@axe-core/playwright";

import { WEB_URL } from "./support/env";
import { expect, test } from "./support/fixtures";
import { waitForNetworkQuiet } from "./support/network";

const PUBLIC_PAGES = ["/en", "/ru/for/hotel", "/ka/terms", "/en/contact"];

for (const theme of ["dark", "light"] as const) {
  test(`the public pages have no serious accessibility violations (${theme})`, async ({ page, context }) => {
    await context.addCookies([{ name: "aw_theme", value: theme, url: WEB_URL }]);
    for (const path of PUBLIC_PAGES) {
      await page.goto(path);
      await expect(page.getByRole("heading", { level: 1 }).first()).toBeVisible();
      await waitForNetworkQuiet(page);
      const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze();
      const serious = results.violations
        .filter((violation) => violation.impact === "serious" || violation.impact === "critical")
        .map((violation) => `${violation.id}: ${violation.nodes.map((node) => node.target.join(" ")).join(" | ")}`);
      expect(serious, path).toEqual([]);
    }
  });
}
