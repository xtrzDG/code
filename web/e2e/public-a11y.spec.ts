/**
 * The public pages pass the same automated audit as the cabinet (axe-core,
 * WCAG 2.2 A and AA: WCAG_TAGS, no serious or critical violation), in both
 * themes, with the cookie banner open as a first visit sees it; the banner
 * itself works from the keyboard, rejects when closed and comes back from
 * the footer's "Cookie settings". The cabinet, the hosted chat and the
 * booking page never show it.
 */

import AxeBuilder from "@axe-core/playwright";

import { WCAG_TAGS } from "./support/axe";
import { renderDeferredBlocks } from "./support/deferredBlocks";
import { WEB_URL } from "./support/env";
import { expect, test } from "./support/fixtures";
import { en, it as italian } from "./support/messages";
import { waitForNetworkQuiet } from "./support/network";

const PUBLIC_PAGES = ["/en", "/it/for/hotel", "/it/terms", "/en/contact", "/en/cookies", "/it/accessibility"];

for (const theme of ["dark", "light"] as const) {
  test(`the public pages have no serious accessibility violations (${theme})`, async ({ page, context }) => {
    await context.addCookies([{ name: "aw_theme", value: theme, url: WEB_URL }]);
    for (const path of PUBLIC_PAGES) {
      await page.goto(path);
      await expect(page.getByRole("heading", { level: 1 }).first()).toBeVisible();
      // A first visit: the banner is part of what is audited.
      await expect(page.getByTestId("cookie-consent")).toBeVisible();
      await waitForNetworkQuiet(page);
      await renderDeferredBlocks(page);
      const results = await new AxeBuilder({ page }).withTags([...WCAG_TAGS]).analyze();
      const serious = results.violations
        .filter((violation) => violation.impact === "serious" || violation.impact === "critical")
        .map((violation) => `${violation.id}: ${violation.nodes.map((node) => node.target.join(" ")).join(" | ")}`);
      expect(serious, path).toEqual([]);
    }
  });
}

test("the cookie banner offers both answers alike, rejects when closed and comes back from the footer", async ({ page, context }) => {
  await page.goto("/it?utm_source=newsletter");
  const banner = page.getByRole("region", { name: italian.cookieConsent.title });
  await expect(banner).toBeVisible();
  const accept = banner.getByRole("button", { name: italian.cookieConsent.accept, exact: true });
  const reject = banner.getByRole("button", { name: italian.cookieConsent.reject, exact: true });
  await expect(accept).toBeVisible();
  await expect(reject).toBeVisible();
  expect(await accept.getAttribute("class")).toBe(await reject.getAttribute("class"));
  // Nothing that needs consent before an answer.
  expect((await context.cookies()).map((cookie) => cookie.name)).not.toContain("aw_attr");

  // Closing is a rejection.
  await banner.getByRole("button", { name: italian.cookieConsent.close }).click();
  await expect(banner).toBeHidden();
  let cookies = await context.cookies();
  expect(cookies.find((cookie) => cookie.name === "aw_consent")?.value).toBe("1.denied");
  expect(cookies.map((cookie) => cookie.name)).not.toContain("aw_attr");

  // The choice is remembered on the next page.
  await page.goto("/it/terms");
  await expect(page.getByRole("heading", { level: 1 }).first()).toBeVisible();
  await expect(page.getByTestId("cookie-consent")).toHaveCount(0);

  // "Cookie settings" in the footer reopens it; accepting from the keyboard keeps the first touch.
  const settings = page.getByTestId("site-footer").getByRole("button", { name: italian.cookieConsent.settings });
  await settings.click();
  await expect(banner).toBeVisible();
  await banner.getByRole("button", { name: italian.cookieConsent.accept, exact: true }).focus();
  await page.keyboard.press("Enter");
  await expect(banner).toBeHidden();
  await expect(settings).toBeFocused();
  cookies = await context.cookies();
  expect(cookies.find((cookie) => cookie.name === "aw_consent")?.value).toBe("1.granted");
  expect(cookies.find((cookie) => cookie.name === "aw_attr")).toMatchObject({ httpOnly: true, sameSite: "Lax" });

  // Escape withdraws it again, and the attribution cookie goes with it.
  await settings.click();
  await expect(banner).toBeVisible();
  await banner.getByRole("button", { name: italian.cookieConsent.reject, exact: true }).focus();
  await page.keyboard.press("Escape");
  await expect(banner).toBeHidden();
  cookies = await context.cookies();
  expect(cookies.find((cookie) => cookie.name === "aw_consent")?.value).toBe("1.denied");
  expect(cookies.map((cookie) => cookie.name)).not.toContain("aw_attr");
});

test("the accessibility statement and the cookie statement are linked from every public page's footer", async ({ page }) => {
  await page.goto("/en");
  const footer = page.getByTestId("site-footer");
  await expect(footer.getByRole("link", { name: en.accessibility.nav })).toHaveAttribute("href", "/en/accessibility");
  await expect(footer.getByRole("link", { name: en.cookieConsent.nav })).toHaveAttribute("href", "/en/cookies");

  await page.goto("/accessibility");
  await expect(page).toHaveURL(/\/en\/accessibility$/);
  const statement = page.getByTestId("accessibility-statement");
  await expect(statement.getByRole("heading", { level: 1, name: en.accessibility.title })).toBeVisible();
  await expect(statement.getByRole("heading", { level: 2, name: en.accessibility.statusTitle })).toBeVisible();
  await expect(statement.getByRole("heading", { level: 2, name: en.accessibility.enforcementTitle })).toBeVisible();
  await expect(statement.getByRole("link", { name: en.accessibility.enforcementLink })).toHaveAttribute("href", "https://form.agid.gov.it/");
});

test("the cabinet's sign-in page shows no cookie banner", async ({ page }) => {
  await page.goto("/login");
  await expect(page.getByRole("heading", { level: 1 }).first()).toBeVisible();
  await expect(page.getByTestId("cookie-consent")).toHaveCount(0);
});
