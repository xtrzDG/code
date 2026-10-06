/**
 * The referral program: an owner's invitation (the Overview card from the
 * tenth booking, the account menu at any time), a partner added by the
 * platform team who signs in to their portal and makes a link for each
 * place they share it, the admin's partners and payouts, and a visitor's
 * `?ref=` kept through the public site in their language.
 */

import { signInAsPlatformAdmin } from "./support/admin";
import { signInByEmail, uniqueEmail, uniqueSuffix } from "./support/api";
import { signInAsDemoOwner } from "./support/demo";
import { API_URL, PLATFORM_ADMIN_EMAIL } from "./support/env";
import { expect, signInContext, test } from "./support/fixtures";
import { en } from "./support/messages";

const referrals = en.referrals;
const portal = en.partnerPortal;
const partners = en.adminPartners;

test("the Overview invites a business once the business has ten bookings", async ({ browser, request }) => {
  const demo = await signInAsDemoOwner(request);
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 }, reducedMotion: "reduce" });
  await signInContext(context, demo.token);
  const page = await context.newPage();
  await page.goto(`/b/${demo.businessId}/overview`);

  const card = page.getByRole("region", { name: referrals.title });
  await expect(card).toBeVisible();
  await expect(card.getByTestId("invite-link")).toContainText("?ref=");
  await expect(card.getByTestId("invite-link")).toContainText("src=invite");
  await expect(card.getByText(referrals.invited)).toBeVisible();
  await context.close();
});

test("a new owner finds the invitation in the account menu, not on the Overview", async ({ page, owner }) => {
  await page.goto(`/b/${owner.businessId}/overview`);
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await expect(page.getByRole("region", { name: referrals.title })).toHaveCount(0);

  await page.getByRole("button", { name: new RegExp(en.account.menu) }).click();
  await page.getByRole("dialog", { name: en.account.menu }).getByRole("button", { name: new RegExp(referrals.menu) }).click();

  const dialog = page.getByRole("dialog", { name: referrals.title });
  await expect(dialog.getByTestId("invite-link")).toContainText("?ref=");
  await dialog.getByRole("button", { name: referrals.showQr }).click();
  await expect(dialog.getByRole("img", { name: referrals.qrLabel })).toBeVisible();
});

test("a partner added by the platform team makes a link for each place they share it", async ({ browser, request }) => {
  const adminToken = await signInAsPlatformAdmin(request, PLATFORM_ADMIN_EMAIL);
  const email = uniqueEmail();
  const code = `agency-${uniqueSuffix()}`;
  const created = await request.post(`${API_URL}/v1/admin/partners`, {
    headers: { authorization: `Bearer ${adminToken}` },
    data: { name: `Agency ${code}`, email, commission_rate_basis_points: 2000, code },
  });
  expect(created.status(), await created.text()).toBe(201);

  const partnerContext = await browser.newContext({ viewport: { width: 390, height: 844 }, reducedMotion: "reduce" });
  await signInContext(partnerContext, await signInByEmail(request, email));
  const page = await partnerContext.newPage();
  await page.goto("/partner");
  await expect(page.getByRole("heading", { level: 1, name: portal.title })).toBeVisible();
  await page.getByRole("textbox", { name: portal.links.source }).fill("instagram");
  await expect(page.getByTestId("partner-link")).toContainText(`ref=${code}&src=instagram`);
  await expect(page.getByText(portal.businesses.empty)).toBeVisible();
  await partnerContext.close();

  const adminContext = await browser.newContext({ viewport: { width: 1280, height: 900 }, reducedMotion: "reduce" });
  await signInContext(adminContext, adminToken);
  const admin = await adminContext.newPage();
  await admin.goto("/admin/partners");
  await expect(admin.getByRole("heading", { level: 1, name: partners.title })).toBeVisible();
  await expect(admin.getByTestId("partner-row").filter({ hasText: code })).toBeVisible();
  await expect(admin.getByRole("combobox", { name: partners.payouts.month })).toBeVisible();
  await adminContext.close();
});

test("an owner who is not a partner gets no portal", async ({ page, owner, consoleErrors }) => {
  expect(owner.businessId).toBeTruthy();
  // The 404 page itself, and the favicon request a 404 page sometimes draws.
  consoleErrors.allow(/status of 404 \(Not Found\) \(http:\/\/localhost:\d+\/(partner|favicon\.ico)\)/);
  const response = await page.goto("/partner");

  expect(response?.status()).toBe(404);
  await expect(page.getByText(en.errors.notFoundTitle)).toBeVisible();
});

test("a visitor's ref survives the redirect to the site in their language", async ({ browser }) => {
  const context = await browser.newContext({ locale: "en-US" });
  const page = await context.newPage();
  await page.goto("/?ref=invite-code-01&src=invite");
  await expect(page).toHaveURL(/\/(en|ka|ru)\?ref=invite-code-01/);

  const cookies = await context.cookies();
  const attribution = cookies.find((cookie) => cookie.name === "aw_attr");
  expect(attribution, "the first touch is kept").toBeDefined();
  expect(Buffer.from(attribution?.value ?? "", "base64url").toString("utf8")).toContain('"referral_code":"invite-code-01"');
  await context.close();
});
