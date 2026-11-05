/**
 * Invoices for the accountant: the owner fills in the billing details
 * ("Реквизиты для счетов") once, malformed values are caught first and the
 * details stay; the demo salon's paid invoice carries its number and the
 * invoice and its receipt download as PDFs through the cabinet.
 */

import { readFile } from "node:fs/promises";

import { API_URL } from "./support/env";
import { signInAsDemoOwner } from "./support/demo";
import { expect, signInContext, test } from "./support/fixtures";
import { en } from "./support/messages";

const billing = en.billing;
const DEMO_SALON = "Studio Lindenblatt";

test("the owner saves the billing details invoices name the business with", async ({ page, owner }) => {
  await page.goto(`/b/${owner.businessId}/settings/billing`);
  const card = page.locator("#billing-details");
  await expect(card.getByText(billing.details.notSaved)).toBeVisible();
  await expect(card.getByLabel(billing.details.legalName)).toHaveValue(owner.businessName);
  await expect(card.getByLabel(billing.details.country)).toHaveValue("DE");
  await expect(card.getByText(billing.details.vat.not_registered)).toBeVisible();

  await card.getByLabel(billing.details.legalName).fill("Salon Morgenrot GmbH");
  await card.getByLabel(billing.details.taxId).fill("DE 123 456 789");
  await card.getByLabel(billing.details.billingEmail).fill("accounts");
  await card.getByLabel(billing.details.address).fill("Oranienstraße 1\n10999 Berlin");
  await card.getByRole("button", { name: billing.details.save }).click();
  await expect(card.getByText(billing.details.errors.billingEmail)).toBeVisible();

  await card.getByLabel(billing.details.billingEmail).fill("Accounts@Morgenrot.example");
  await card.getByRole("button", { name: billing.details.save }).click();
  await expect(page.getByText(billing.details.saved)).toBeVisible();
  await expect(card.getByText(billing.details.notSaved)).toBeHidden();
  await expect(card.getByRole("button", { name: billing.details.save })).toBeDisabled();

  await page.reload();
  await expect(card.getByLabel(billing.details.legalName)).toHaveValue("Salon Morgenrot GmbH");
  await expect(card.getByLabel(billing.details.taxId)).toHaveValue("DE 123 456 789");
  await expect(card.getByLabel(billing.details.billingEmail)).toHaveValue("accounts@morgenrot.example");
  await expect(card.getByLabel(billing.details.address)).toHaveValue("Oranienstraße 1\n10999 Berlin");
});

test("the paid invoice and its receipt download as numbered PDFs", async ({ page, context, request }) => {
  const demo = await signInAsDemoOwner(request);
  await signInContext(context, demo.token);
  const response = await request.get(`${API_URL}/v1/businesses`, { headers: { authorization: `Bearer ${demo.token}` } });
  const salon = ((await response.json()) as { id: string; name: string }[]).find((business) => business.name === DEMO_SALON);
  expect(salon, "the demo salon is seeded").toBeDefined();

  await page.goto(`/b/${salon!.id}/settings/billing`);
  const number = page.getByText(/No\. AW-\d{4}-\d{6}/);
  await expect(number).toBeVisible();

  const [invoice] = await Promise.all([page.waitForEvent("download"), page.getByRole("button", { name: /^Download invoice AW-/ }).click()]);
  expect(invoice.suggestedFilename()).toMatch(/^invoice-AW-\d{4}-\d{6}\.pdf$/);
  expect((await readFile(await invoice.path())).subarray(0, 5).toString()).toBe("%PDF-");

  const [receipt] = await Promise.all([page.waitForEvent("download"), page.getByRole("button", { name: /^Receipt for invoice AW-/ }).click()]);
  expect(receipt.suggestedFilename()).toMatch(/^receipt-AW-\d{4}-\d{6}\.pdf$/);
  expect((await readFile(await receipt.path())).subarray(0, 5).toString()).toBe("%PDF-");
  await expect(page.locator("#billing-details").getByLabel(billing.details.legalName)).toHaveValue("Studio Lindenblatt GmbH");
});
