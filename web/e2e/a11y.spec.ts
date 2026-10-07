/**
 * Automated accessibility audit (axe-core, WCAG 2.1 A and AA rules) of the
 * setup, the businesses, sign-in, the offline page and the phone layout in
 * both themes and in Hebrew (right to left): no serious or critical
 * violation is allowed. Every section of a business is audited in
 * a11y-sections-en.spec.ts and a11y-sections-he.spec.ts (support/axe.ts).
 */

import { audit, seriousViolations } from "./support/axe";
import { WEB_URL } from "./support/env";
import { expect, test } from "./support/fixtures";
import { en, he } from "./support/messages";

test("the setup invitation, the tunnel, the businesses, sign-in and the offline page pass the audit", async ({
  page,
  newOwner,
}) => {
  await audit(page, `/b/${newOwner.businessId}/overview`);
  for (const step of [
    "business",
    "place",
    "offer",
    "hours",
    "people",
    "channels",
    "try",
    "launch",
  ]) {
    await test.step(step, () =>
      audit(page, `/b/${newOwner.businessId}/setup?step=${step}`),
    );
  }
  await audit(page, "/create");
  await audit(page, "/businesses");
  await audit(page, "/offline");
  await page.context().clearCookies();
  await audit(page, "/login");
});

test.describe("on a phone", () => {
  test.use({
    viewport: { width: 390, height: 844 },
    isMobile: true,
    hasTouch: true,
  });

  test("the main pages and the More sheet pass the audit", async ({
    page,
    owner,
  }) => {
    for (const path of ["overview", "inbox", "assistant", "settings"]) {
      await test.step(path, () =>
        audit(page, `/b/${owner.businessId}/${path}`),
      );
    }
    await page.getByRole("button", { name: en.navigation.more }).click();
    await expect(
      page.getByRole("dialog", { name: en.navigation.more }),
    ).toBeVisible();
    expect(await seriousViolations(page)).toEqual([]);
  });

  test("the main pages and the More sheet pass the audit in Hebrew", async ({
    page,
    owner,
  }) => {
    await page
      .context()
      .addCookies([{ name: "aw_locale", value: "he", url: WEB_URL }]);
    for (const path of [
      "overview",
      "inbox",
      "bookings",
      "assistant",
      "settings",
    ]) {
      await test.step(path, () =>
        audit(page, `/b/${owner.businessId}/${path}`),
      );
    }
    await page.getByRole("button", { name: he.navigation.more }).click();
    await expect(
      page.getByRole("dialog", { name: he.navigation.more }),
    ).toBeVisible();
    expect(await seriousViolations(page)).toEqual([]);
  });

  for (const theme of ["dark", "light"] as const) {
    test(`the front desk pages, the page's (i) and the filters pass the audit in the ${theme} theme`, async ({
      page,
      owner,
    }) => {
      test.setTimeout(120_000);
      await page
        .context()
        .addCookies([{ name: "aw_theme", value: theme, url: WEB_URL }]);
      for (const path of [
        "bookings",
        "bookings?view=all",
        "bookings?view=week",
        "assistant/knowledge",
        "assistant/channels",
      ]) {
        await test.step(path, () =>
          audit(page, `/b/${owner.businessId}/${path}`),
        );
      }
      await page.getByRole("button", { name: en.chrome.pageInfo }).click();
      await expect(page.getByRole("dialog")).toBeVisible();
      expect(await seriousViolations(page), "the page's (i)").toEqual([]);

      await page.goto(`/b/${owner.businessId}/bookings?view=all`);
      await page
        .getByRole("button", { name: en.chrome.filters.open, exact: true })
        .click();
      await expect(
        page.getByRole("dialog", { name: en.chrome.filters.title }),
      ).toBeVisible();
      expect(await seriousViolations(page), "the filters").toEqual([]);
    });
  }
});
