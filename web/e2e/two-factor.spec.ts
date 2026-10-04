/**
 * Two-factor sign-in, with an authenticator app played by the test
 * (support/totp.ts): an owner sets the app up in Account → Security, saves
 * the recovery codes, confirms a sensitive action with it, and signs in
 * again with the login code and the app's code; a platform admin sets the
 * app up during the first sign-in and reaches the admin pages.
 */

import type { Locator, Page } from "@playwright/test";

import { ensureOnAdminTeam } from "./support/admin";
import { MFA_ADMIN_EMAIL } from "./support/env";
import { expect, test } from "./support/fixtures";
import { apiLogSize, waitForLoginCode } from "./support/login-codes";
import { en } from "./support/messages";
import { freshTotpCode, totpCode } from "./support/totp";

test.describe.configure({ timeout: 180_000 });

/** An address may ask for a login code every 30 seconds. */
const LOGIN_CODE_COOLDOWN_MS = 31_000;

/** The key shown next to the QR code, without its spaces. */
async function readKey(container: Locator): Promise<string> {
  const key = container.locator("p[translate=no]").first();
  await expect(key).toHaveText(/^[A-Z2-7 ]{32,}$/);
  return (await key.innerText()).replace(/\s/g, "");
}

/** Recovery codes, shown once: ten of them; going on needs "I saved them". */
async function saveRecoveryCodes(container: Locator, goOn: string): Promise<void> {
  await expect(container.getByRole("list", { name: en.mfa.recovery.title }).getByRole("listitem")).toHaveCount(10);
  const button = container.getByRole("button", { name: goOn, exact: true });
  await expect(button).toBeDisabled();
  await container.getByRole("checkbox", { name: en.mfa.recovery.saved }).check();
  await button.click();
}

/** Asks for a login code by e-mail on the sign-in page and types it in. */
async function passLoginCode(page: Page, email: string): Promise<void> {
  await page.getByRole("group", { name: en.auth.methodLabel }).getByText(en.auth.methodEmail, { exact: true }).click();
  await page.getByRole("textbox", { name: en.auth.email, exact: true }).fill(email);
  const since = apiLogSize();
  await page.getByRole("button", { name: en.auth.sendCode }).click();
  await page.getByLabel(en.auth.code, { exact: true }).fill(await waitForLoginCode({ since }));
}

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

test("an owner sets up an authenticator app, confirms an action with it and signs in with it", async ({
  page,
  browser,
  owner,
  consoleErrors,
}) => {
  const signedInAt = Date.now();
  // The refused requests below (a wrong code, the stand-in 401) are reported by the browser.
  consoleErrors.allow(/Failed to load resource: the server responded with a status of 4\d\d/);

  await page.goto("/account/security");
  await expect(page.getByRole("heading", { level: 1, name: en.security.title })).toBeVisible();
  // Scoped to the page: right after a full load the streamed copy of a card can
  // still sit hidden outside it, next to the one shown.
  await expect(page.getByRole("main").getByText(en.security.session.oneFactor)).toBeVisible();
  await page.getByRole("button", { name: en.security.app.setUp }).click();

  const setup = page.getByRole("dialog", { name: en.mfa.setup.title });
  await expect(setup.getByRole("img", { name: en.mfa.setup.qrLabel })).toBeVisible();
  const key = await readKey(setup);
  const current = totpCode(key);
  await setup.getByLabel(en.mfa.setup.code).fill(current === "000000" ? "111111" : "000000");
  await expect(setup.getByText(en.mfa.errors.wrongCode)).toBeVisible();
  const first = await freshTotpCode(key, null);
  await setup.getByLabel(en.mfa.setup.code).fill(first.code);

  const codes = page.getByRole("dialog", { name: en.mfa.recovery.title });
  await saveRecoveryCodes(codes, en.common.done);
  await expect(codes).toBeHidden();
  await expect(page.getByText(en.security.app.on, { exact: true })).toBeVisible();
  await expect(page.getByText(en.security.codes.left.other.replace("{count}", "10"))).toBeVisible();
  await expect(page.getByText(en.security.session.twoFactor)).toBeVisible();

  // A sensitive action refused for an old sign-in: the dialog asks for the app's code, then the action runs.
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
  const staffEmail = `staff-${first.step}@e2e-two-factor.example.com`;
  await invite.getByRole("textbox", { name: en.settings.team.email }).fill(staffEmail);
  await invite.getByRole("button", { name: en.settings.team.send, exact: true }).click();

  const confirm = page.getByRole("dialog", { name: en.mfa.stepUp.title });
  await expect(confirm.getByText(en.mfa.stepUp.totp)).toBeVisible();
  const second = await freshTotpCode(key, first.step);
  await confirm.getByLabel(en.mfa.stepUp.code).fill(second.code);
  await expect(confirm).toBeHidden();
  await expect(page.getByText(en.mfa.stepUp.confirmed)).toBeVisible();
  await expect(page.getByText(staffEmail, { exact: true })).toBeVisible();
  expect(refused).toBe(true);
  // The new member has no app yet: the team card counts them.
  await expect(page.getByText(en.security.team.without.one.replace("{count}", "1"))).toBeVisible();

  // Signing in again takes the login code and then the app's code.
  const fresh = await browser.newContext({ viewport: { width: 390, height: 844 }, reducedMotion: "reduce" });
  const phone = await fresh.newPage();
  await phone.goto("/login?next=/account/security");
  const wait = LOGIN_CODE_COOLDOWN_MS - (Date.now() - signedInAt);
  if (wait > 0) {
    await phone.waitForTimeout(wait);
  }
  await passLoginCode(phone, owner.email);
  await expect(phone.getByRole("heading", { name: en.mfa.secondStep.title })).toBeVisible();
  await expect(phone.getByLabel(en.mfa.secondStep.code)).toBeFocused();
  const third = await freshTotpCode(key, second.step);
  await phone.getByLabel(en.mfa.secondStep.code).fill(third.code);
  await expect(phone).toHaveURL(/\/account\/security$/);
  await expect(phone.getByRole("main").getByText(en.security.session.twoFactor)).toBeVisible();
  await fresh.close();
});

test("a platform admin sets up the app at the first sign-in and opens the admin pages", async ({ page, request }) => {
  // A SUPER admin added this person on the Team page.
  await ensureOnAdminTeam(request, MFA_ADMIN_EMAIL);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/login?next=/admin");
  await passLoginCode(page, MFA_ADMIN_EMAIL);

  await expect(page.getByRole("heading", { name: en.mfa.enrollment.title })).toBeVisible();
  await page.getByRole("button", { name: en.mfa.enrollment.start }).click();
  const key = await readKey(page.locator("main"));
  const { code } = await freshTotpCode(key, null);
  await page.getByLabel(en.mfa.setup.code).fill(code);

  await expect(page.getByRole("heading", { name: en.mfa.recovery.title })).toBeVisible();
  await saveRecoveryCodes(page.locator("main"), en.mfa.recovery.continue);
  await expect(page).toHaveURL(/\/admin$/);
  await expect(page.getByRole("heading", { level: 1, name: en.pages.admin.title })).toBeVisible();
});
