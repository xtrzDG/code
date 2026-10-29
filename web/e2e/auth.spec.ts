import type { Page } from "@playwright/test";

import { uniqueEmail } from "./support/api";
import { expect, test } from "./support/fixtures";
import { apiLogSize, waitForLoginCode } from "./support/login-codes";
import { en } from "./support/messages";

/** Eight random digits for a fresh German mobile number (+49 151 …). */
function randomMobileDigits(): string {
  return String(Math.floor(Math.random() * 1e8)).padStart(8, "0");
}

/** The phone/e-mail switch is a pair of visually hidden radios inside their labels. */
async function chooseEmail(page: Page): Promise<void> {
  await page.getByRole("group", { name: en.auth.methodLabel }).getByText(en.auth.methodEmail, { exact: true }).click();
  await expect(page.getByRole("radio", { name: en.auth.methodEmail })).toBeChecked();
}

test.describe("sign-in", () => {
  test("by phone with a German number", async ({ page }) => {
    const digits = randomMobileDigits();
    await page.goto("/businesses");
    // Signed-out visitors land on the sign-in page.
    await expect(page).toHaveURL(/\/login(\?|$)/);

    await page.getByLabel(en.auth.country).selectOption("DE");
    await expect(page.getByText(en.auth.phoneHint.replace("{code}", "49"))).toBeVisible();
    await page.getByLabel(en.auth.phone).fill(`0151 ${digits}`);
    const since = apiLogSize();
    await page.getByRole("button", { name: en.auth.sendCode }).click();

    await expect(page.getByRole("heading", { name: en.auth.codeTitle })).toBeVisible();
    await expect(page.getByText(/\+49/)).toBeVisible();
    const code = await waitForLoginCode({ since });
    await page.getByLabel(en.auth.code, { exact: true }).fill(code);

    // A new account starts in "Create an AI assistant".
    await expect(page).toHaveURL(/\/create$/);
    await expect(page.getByRole("heading", { level: 1, name: en.tunnelBusiness.business.title })).toBeVisible();
  });

  test("by e-mail", async ({ page }) => {
    const email = uniqueEmail();
    await page.goto("/login");
    await chooseEmail(page);
    await page.getByRole("textbox", { name: en.auth.email, exact: true }).fill(email);
    const since = apiLogSize();
    await page.getByRole("button", { name: en.auth.sendCode }).click();

    await expect(page.getByRole("heading", { name: en.auth.codeTitle })).toBeVisible();
    const code = await waitForLoginCode({ since });
    await page.getByLabel(en.auth.code, { exact: true }).fill(code);

    await expect(page).toHaveURL(/\/create$/);
    await expect(page.getByRole("heading", { level: 1, name: en.tunnelBusiness.business.title })).toBeVisible();
  });

  test("refuses a wrong code and accepts the right one", async ({ page, consoleErrors }) => {
    // The browser reports the refused verification request itself.
    consoleErrors.allow(/Failed to load resource: the server responded with a status of 4\d\d/);
    const email = uniqueEmail();
    await page.goto("/login");
    await chooseEmail(page);
    await page.getByRole("textbox", { name: en.auth.email, exact: true }).fill(email);
    const since = apiLogSize();
    await page.getByRole("button", { name: en.auth.sendCode }).click();
    const code = await waitForLoginCode({ since });
    const wrong = code === "000000" ? "111111" : "000000";

    await page.getByLabel(en.auth.code, { exact: true }).fill(wrong);
    await expect(page.getByText(en.auth.errors.wrongCode)).toBeVisible();
    await page.getByLabel(en.auth.code, { exact: true }).fill(code);
    await expect(page).toHaveURL(/\/create$/);
  });
});
