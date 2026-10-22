/**
 * Passkeys as the second factor (R7 sign-in), with Chromium's virtual
 * authenticator playing the device (support/webauthn.ts): an owner adds a
 * passkey in Account → Security, signs in again with the login code and
 * the passkey, and a copy of the passkey with an older signature counter
 * (a cloned authenticator) is refused at the next sign-in.
 */

import type { Locator, Page } from "@playwright/test";

import { expect, test } from "./support/fixtures";
import { passLoginCode } from "./support/login-codes";
import { en } from "./support/messages";
import { addVirtualAuthenticator } from "./support/webauthn";

test.describe.configure({ timeout: 180_000 });

/** An address may ask for a login code every 30 seconds. */
const LOGIN_CODE_COOLDOWN_MS = 31_000;

/** The recovery codes shown with the first second factor: saved, then closed. */
async function saveRecoveryCodes(dialog: Locator): Promise<void> {
  await expect(dialog.getByRole("list", { name: en.mfa.recovery.title }).getByRole("listitem")).toHaveCount(10);
  await dialog.getByRole("checkbox", { name: en.mfa.recovery.saved }).check();
  await dialog.getByRole("button", { name: en.common.done, exact: true }).click();
  await expect(dialog).toBeHidden();
}

/** Signs out (the session cookie goes) and signs in again up to the second step. */
async function signInAgain(page: Page, email: string, lastCodeAt: number): Promise<void> {
  await page.context().clearCookies({ name: "aw_session" });
  await page.goto("/login?next=/account/security");
  const wait = LOGIN_CODE_COOLDOWN_MS - (Date.now() - lastCodeAt);
  if (wait > 0) {
    await page.waitForTimeout(wait);
  }
  await passLoginCode(page, email);
  await expect(page.getByRole("heading", { name: en.mfa.secondStep.title })).toBeVisible();
}

test("an owner adds a passkey, signs in with it, and a cloned copy is refused", async ({ page, owner, consoleErrors }) => {
  const signedInAt = Date.now();
  // The refused sign-in (422) is reported by the browser itself.
  consoleErrors.allow(/Failed to load resource: the server responded with a status of 422/);
  const authenticator = await addVirtualAuthenticator(page);

  await page.goto("/account/security");
  const card = page.getByRole("main").locator("section", { has: page.getByRole("heading", { name: en.passkeys.title }) });
  await expect(card.getByText(en.passkeys.empty)).toBeVisible();
  await card.getByRole("button", { name: en.passkeys.add }).click();
  await saveRecoveryCodes(page.getByRole("dialog", { name: en.mfa.recovery.title }));
  await expect(page.getByText(en.passkeys.added)).toBeVisible();
  await expect(card.getByRole("list", { name: en.passkeys.title }).getByRole("listitem")).toHaveCount(1);
  await expect(page.getByRole("main").getByText(en.security.session.twoFactor)).toBeVisible();
  const [credential] = await authenticator.credentials();
  expect(credential?.rpId).toBe("localhost");

  // The next sign-in offers the passkey first; the device answers at once.
  await signInAgain(page, owner.email, signedInAt);
  const codeAt = Date.now();
  await page.getByRole("button", { name: en.passkeys.signIn.use }).click();
  await expect(page).toHaveURL(/\/account\/security$/);
  await expect(page.getByRole("main").getByText(en.security.session.twoFactor)).toBeVisible();

  // A copy made before that sign-in: its counter is behind the server's.
  const [used] = await authenticator.credentials();
  expect(used?.signCount).toBeGreaterThan(0);
  await authenticator.rewindCounter(used!, 0);
  await signInAgain(page, owner.email, codeAt);
  await page.getByRole("button", { name: en.passkeys.signIn.use }).click();
  await expect(page.getByText(en.passkeys.errors.suspended)).toBeVisible();
  await expect(page).toHaveURL(/\/login/);
});
