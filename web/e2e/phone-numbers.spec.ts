/**
 * "Get a number" on the phone channel card and in the setup tunnel. The
 * e2e server rents no numbers by itself (no PHONE_NUMBER_PROVIDER), so a
 * search there says our team arranges the number and the owner sends a
 * request, then cancels it. Taking a number on offer is served by the test
 * (the carrier is not reachable here): the dialog shows the monthly price,
 * asks to confirm and sends the price the owner saw.
 */

import type { Page } from "@playwright/test";

import type { Schema } from "../src/api/types";

import { expect, test } from "./support/fixtures";
import { en } from "./support/messages";
import { expectNoSidewaysScroll } from "./support/tunnel";

const phone = en.phoneNumbers;
const AUSTIN: Schema<"PhoneNumberOfferList"> = {
  country_code: "US",
  number_type: "local",
  availability: "self_serve",
  monthly_price: { money: { amount_minor: 1200, currency_code: "EUR" }, text: "€12.00", is_estimated: false },
  offers: [{ phone_number: "+15125550142", display_number: "+1 512-555-0142", offer_token: "1767225600.AAAAAAAAAAAAAAAAAAAAAA", locality: "Austin", region: "TX" }],
};

async function openGetNumber(page: Page) {
  await page.getByRole("button", { name: phone.panel.getNumber }).click();
  const dialog = page.getByRole("dialog", { name: phone.dialog.title });
  await expect(dialog).toBeVisible();
  return dialog;
}

test("where our team arranges numbers the owner asks it, then cancels", async ({ page, owner }) => {
  await page.goto(`/b/${owner.businessId}/assistant/channels`);
  await expect(page.getByText(phone.panel.noNumber)).toBeVisible();

  const dialog = await openGetNumber(page);
  // A self-serve country, but this server has no carrier: the team arranges it.
  await dialog.getByLabel(phone.dialog.country).selectOption("US");
  await dialog.getByLabel(phone.dialog.city, { exact: false }).fill("Austin");
  await dialog.getByRole("button", { name: phone.dialog.search }).click();
  await expect(dialog.getByText(phone.request.on_request)).toBeVisible();
  await dialog.getByRole("button", { name: phone.request.ask }).click();

  await expect(dialog).toBeHidden();
  await expect(page.getByText(phone.panel.requestTitle)).toBeVisible();
  await expect(page.getByText(/near Austin/)).toBeVisible();

  await page.reload();
  await expect(page.getByText(phone.panel.requestTitle)).toBeVisible();
  await page.getByRole("button", { name: phone.panel.cancelRequest }).click();
  await expect(page.getByRole("button", { name: phone.panel.getNumber })).toBeVisible();
});

test.describe("on a phone", () => {
  test.use({ viewport: { width: 390, height: 844 } });

  test("the owner sees the monthly price, confirms and the number is taken", async ({ page, owner }) => {
    let sent: unknown = null;
    await page.route("**/api/backend/v1/businesses/*/phone-line/offers*", (route) => route.fulfill({ json: AUSTIN }));
    await page.route("**/api/backend/v1/businesses/*/phone-line/number*", async (route) => {
      sent = route.request().postDataJSON();
      const rented: Schema<"RentedPhoneNumberView"> = {
        phone_number: "+15125550142",
        display_number: "+1 512-555-0142",
        country_code: "US",
        number_type: "local",
        locality: "Austin",
        monthly_price: AUSTIN.monthly_price!,
        status: "active",
        is_attached: false,
        has_answering_agent: true,
        rented_at: 1,
      };
      await route.fulfill({ status: 201, json: rented });
    });
    await page.goto(`/b/${owner.businessId}/assistant/channels`);

    const dialog = await openGetNumber(page);
    await dialog.getByLabel(phone.dialog.country).selectOption("US");
    await dialog.getByRole("button", { name: phone.dialog.search }).click();
    await expect(dialog.getByText("+1 512-555-0142")).toBeVisible();
    await expect(dialog.getByText(/a month for any of them/)).toBeVisible();
    await expectNoSidewaysScroll(page);

    await dialog.getByRole("button", { name: `Take +1 512-555-0142` }).click();
    await expect(dialog.getByText(/billed with your plan from today/)).toBeVisible();
    await dialog.getByRole("button", { name: phone.confirm.take }).click();

    await expect(dialog).toBeHidden();
    expect(sent).toEqual({
      phone_number: "+15125550142",
      number_type: "local",
      // The token of the offer the search gave: the server takes only that.
      offer_token: "1767225600.AAAAAAAAAAAAAAAAAAAAAA",
      monthly_price: { amount_minor: 1200, currency_code: "EUR" },
      locality: "Austin",
    });
  });
});

test("the tunnel's channels step offers a number for calls", async ({ page, newOwner }) => {
  await page.goto(`/b/${newOwner.businessId}/setup?step=channels`);
  await expect(page.getByRole("heading", { name: phone.tunnel.title })).toBeVisible();
  await expect(page.getByRole("button", { name: phone.panel.getNumber })).toBeVisible();
});
