/**
 * Passkeys as the second factor (R7 sign-in), with Chromium's virtual
 * authenticator playing the device (support/webauthn.ts): an owner adds a
 * passkey in Account → Security, signs in again with the login code and
 * the passkey, and a copy of the passkey with an older signature counter
 * (a cloned authenticator) is refused at the next sign-in. A passkey-only
 * owner confirms a sensitive action with the passkey (a recovery code is
 * the alternative, never a login code) and sees their recovery codes.
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
  // Recovery codes stand in for the passkey, so they are counted here too.
  await expect(page.getByRole("main").getByText(en.security.codes.left.other.replace("{count}", "10"))).toBeVisible();
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

/** The 401 the API answers when a sensitive action needs a fresh confirmation. */
const STEP_UP_REFUSAL = {
  status: 401,
  headers: { "content-type": "application/json", "www-authenticate": 'Bearer error="insufficient_user_authentication", max_age=600' },
  body: JSON.stringify({
    error: "authentication_required",
    message: "Confirm it is you.",
    reasons: [{ code: "step_up_required", message: "Confirm it is you.", details: ["600"] }],
  }),
};

test("a passkey-only owner confirms a sensitive action with the passkey, not a login code", async ({
  page,
  owner,
  consoleErrors,
}) => {
  // The stand-in 401 below is reported by the browser.
  consoleErrors.allow(/Failed to load resource: the server responded with a status of 401/);
  await addVirtualAuthenticator(page);
  await page.goto("/account/security");
  const card = page.getByRole("main").locator("section", { has: page.getByRole("heading", { name: en.passkeys.title }) });
  await card.getByRole("button", { name: en.passkeys.add }).click();
  await saveRecoveryCodes(page.getByRole("dialog", { name: en.mfa.recovery.title }));

  let refused = false;
  await page.route("**/api/backend/v1/businesses/*/members", async (route) => {
    if (route.request().method() === "POST" && !refused) {
      refused = true;
      await route.fulfill(STEP_UP_REFUSAL);
      return;
    }
    await route.fallback();
  });
  await page.goto(`/b/${owner.businessId}/settings/team`);
  await page.getByRole("button", { name: en.settings.team.invite, exact: true }).click();
  const invite = page.getByRole("dialog", { name: en.settings.team.inviteTitle });
  await invite.getByText(en.settings.team.methodEmail, { exact: true }).click();
  await invite.getByRole("textbox", { name: en.settings.team.email }).fill(`staff-${Date.now()}@e2e-passkeys.example.com`);
  await invite.getByRole("button", { name: en.settings.team.send, exact: true }).click();

  const confirm = page.getByRole("dialog", { name: en.mfa.stepUp.title });
  await expect(confirm.getByText(en.passkeys.stepUp.description)).toBeVisible();
  // The way out is a recovery code; no login code is offered or sent.
  await expect(confirm.getByRole("button", { name: en.mfa.secondStep.useRecovery })).toBeVisible();
  await expect(confirm.getByRole("button", { name: en.mfa.stepUp.resend })).toHaveCount(0);
  await confirm.getByRole("button", { name: en.passkeys.stepUp.use }).click();
  await expect(confirm).toBeHidden();
  await expect(page.getByText(en.mfa.stepUp.confirmed)).toBeVisible();
  await expect(invite).toBeHidden();
});
