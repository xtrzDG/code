/**
 * The platform's legal texts against the real API: the sign-in page's code
 * step says continuing accepts the terms, opens the terms and the privacy
 * policy in a dialog without losing the code step, and the accepted
 * version is stored on the account; a hosted chat's privacy notice in a
 * widget language without a reviewed text shows its draft, marked as such,
 * with the English text a click away; the published security contact.
 */

import { uniqueEmail } from "./support/api";
import { expect, test } from "./support/fixtures";
import { openChatBusiness } from "./support/hosted-chat";
import { apiLogSize, waitForLoginCode } from "./support/login-codes";
import { en } from "./support/messages";

test("continuing with the code accepts the terms the page names", async ({ page }) => {
  await page.goto("/login");
  await page.getByRole("group", { name: en.auth.methodLabel }).getByText(en.auth.methodEmail, { exact: true }).click();
  await page.getByRole("textbox", { name: en.auth.email, exact: true }).fill(uniqueEmail());
  const since = apiLogSize();
  await page.getByRole("button", { name: en.auth.sendCode }).click();
  await expect(page.getByRole("heading", { name: en.auth.codeTitle })).toBeVisible();

  const line = page.getByTestId("terms-line");
  await expect(line).toContainText("By continuing, you accept the Terms of Service");
  await line.getByRole("button", { name: en.legalConsent.terms }).click();
  const dialog = page.getByRole("dialog", { name: "Terms of Service" });
  await expect(dialog.getByRole("heading", { level: 3, name: "1. About these terms" })).toBeVisible();
  await expect(dialog.getByText(/^Version \d{4}-\d{2}-\d{2}$/)).toBeVisible();
  await dialog.locator("footer").getByRole("button", { name: en.common.close }).click();
  await expect(dialog).toBeHidden();
  await line.getByRole("button", { name: en.legalConsent.privacy }).click();
  await expect(page.getByRole("dialog", { name: "Privacy Policy" })).toBeVisible();
  await page.keyboard.press("Escape");

  await page.getByLabel(en.auth.code, { exact: true }).fill(await waitForLoginCode({ since }));
  await expect(page).toHaveURL(/\/create$/);
  const me = await page.evaluate(async () => (await fetch("/api/backend/v1/me")).json());
  expect(me.user.accepted_terms_version).toMatch(/^\d{4}-\d{2}-\d{2}$/);
});

test.describe("a privacy notice in a language without a reviewed text", () => {
  test.use({ locale: "he-IL" });

  test("shows the Hebrew draft right to left and links to the English text", async ({ page, request, account }) => {
    const business = await openChatBusiness(request, account.token);

    await page.goto(`/c/${business.slug}/privacy`);

    await expect(page.locator("main")).toHaveAttribute("lang", "he");
    await expect(page.locator("main")).toHaveAttribute("dir", "rtl");
    await expect(page.getByRole("heading", { level: 1, name: "הודעת פרטיות" })).toBeVisible();
    const note = page.getByTestId("privacy-draft-note");
    await expect(note).toContainText("טיוטה");
    await note.getByRole("link", { name: "לקריאה באנגלית" }).click();

    await expect(page).toHaveURL(new RegExp(`/c/${business.slug}/privacy\\?lang=en$`));
    await expect(page.locator("main")).toHaveAttribute("lang", "en");
    await expect(page.getByRole("heading", { level: 1, name: "Privacy notice" })).toBeVisible();
    await expect(page.getByTestId("privacy-draft-note")).toHaveCount(0);
  });
});

test("the cabinet publishes its security contact", async ({ request }) => {
  const response = await request.get("/.well-known/security.txt");

  expect(response.ok()).toBe(true);
  const text = await response.text();
  expect(text).toMatch(/^Contact: https:\/\//m);
  expect(text).toMatch(/^Expires: \d{4}-\d{2}-\d{2}T/m);
});
