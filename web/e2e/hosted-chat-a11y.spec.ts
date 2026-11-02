/**
 * The hosted chat page (/c/{address}) and its privacy notice pass the
 * automated audit against the real API (axe-core, WCAG 2.2 A and AA:
 * WCAG_TAGS, no serious or critical violation) in the light and the dark
 * scheme, with the chat open and a message written; the page links the
 * business's privacy notice and the accessibility statement, and shows
 * no cookie banner.
 */

import { seriousViolations } from "./support/axe";
import { expect, test } from "./support/fixtures";
import { openChatBusiness } from "./support/hosted-chat";
import { waitForNetworkQuiet } from "./support/network";

for (const colorScheme of ["light", "dark"] as const) {
  test(`the hosted chat page has no serious accessibility violations (${colorScheme})`, async ({ page, request, account }) => {
    await page.emulateMedia({ colorScheme });
    const business = await openChatBusiness(request, account.token, ["en"]);

    await page.goto(`/c/${business.slug}`);
    await expect(page.getByRole("heading", { level: 1, name: business.name })).toBeVisible();
    await expect(page.getByRole("textbox")).toBeEditable();
    // A message of the visitor's: the conversation's own elements are audited too.
    await page.getByRole("textbox").fill("Do you have a table for two tonight?");
    await expect(page.getByRole("textbox")).toHaveValue("Do you have a table for two tonight?");
    await waitForNetworkQuiet(page);
    expect(await seriousViolations(page), `/c/${business.slug}`).toEqual([]);

    await page.goto(`/c/${business.slug}/privacy`);
    await expect(page.getByRole("heading", { level: 1, name: "Privacy notice" })).toBeVisible();
    await waitForNetworkQuiet(page);
    expect(await seriousViolations(page), `/c/${business.slug}/privacy`).toEqual([]);
  });
}

test("the hosted chat page links the privacy notice and the accessibility statement, without a cookie banner", async ({
  page,
  request,
  account,
}) => {
  const business = await openChatBusiness(request, account.token, ["en"]);

  await page.goto(`/c/${business.slug}`);
  await expect(page.getByRole("heading", { level: 1, name: business.name })).toBeVisible();

  const links = page.getByTestId("customer-page-links");
  await expect(links.getByRole("link", { name: "Privacy notice" })).toHaveAttribute("href", `/c/${business.slug}/privacy`);
  await expect(links.getByRole("link", { name: "Accessibility" })).toHaveAttribute("href", "/en/accessibility");
  await expect(page.getByTestId("cookie-consent")).toHaveCount(0);
  expect((await page.context().cookies()).map((cookie) => cookie.name)).not.toContain("aw_attr");
});
