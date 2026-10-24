/**
 * The cabinet's accessibility audit (axe-core, WCAG 2.1 A and AA rules): no
 * serious or critical violation is allowed. What axe cannot judge (reading
 * order, meaning of texts) is checked by hand; see web/README.md.
 *
 * The audit of every section in both themes runs once per language, each
 * in a spec file of its own (a11y-sections-*.spec.ts), so that CI can put
 * them on different shards (support/shards.ts); a11y.spec.ts audits the
 * setup, the businesses, sign-in and the phone layout.
 */

import AxeBuilder from "@axe-core/playwright";
import type { Page } from "@playwright/test";

import { WEB_URL } from "./env";
import { expect, test } from "./fixtures";
import { waitForNetworkQuiet } from "./network";

/** Every section of a business, as the owner opens it. */
const OWNER_PAGES = [
  "overview",
  "inbox",
  "inbox?view=all",
  "bookings",
  "customers",
  "customers/segments",
  "assistant",
  "assistant/knowledge",
  "assistant/profile",
  "assistant/channels",
  "assistant/versions",
  "settings",
  "settings/team",
  "settings/notifications",
  "settings/quick-replies",
  "settings/calls",
  "settings/reviews",
  "settings/integrations",
  "settings/billing",
  "settings/privacy",
  "settings/audit",
];

/** Serious and critical violations of a page, one line each. */
export async function seriousViolations(page: Page): Promise<string[]> {
  const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze();
  return results.violations
    .filter((violation) => violation.impact === "serious" || violation.impact === "critical")
    .map(
      (violation) =>
        `${violation.id} (${violation.impact}): ${violation.nodes.map((node) => node.target.join(" ")).join(" | ")}`,
    );
}

/** Opens a page, waits until it settles and audits it. */
export async function audit(page: Page, path: string): Promise<void> {
  await page.goto(path);
  await expect(page.getByRole("heading", { level: 1 }).first()).toBeVisible();
  await waitForNetworkQuiet(page);
  expect(await seriousViolations(page), path).toEqual([]);
}

/** Every section of a business passes the audit in the dark and the light theme, read in this language. */
export function auditEverySection(locale: "en" | "he"): void {
  for (const theme of ["dark", "light"] as const) {
    test(`every section passes the audit in the ${theme} theme, in ${locale}`, async ({ page, owner }) => {
      test.setTimeout(180_000);
      await page.context().addCookies([
        { name: "aw_theme", value: theme, url: WEB_URL },
        { name: "aw_locale", value: locale, url: WEB_URL },
      ]);
      for (const path of OWNER_PAGES) {
        await test.step(path, () => audit(page, `/b/${owner.businessId}/${path}`));
      }
      await expect(page.locator("html")).toHaveAttribute("dir", locale === "he" ? "rtl" : "ltr");
    });
  }
}
