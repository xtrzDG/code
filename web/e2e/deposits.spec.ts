/**
 * Deposits in the cabinet, against the real API where it can be:
 *
 *  - Settings → Deposits: the owner adds a payment page that fills in the
 *    amount (a page without {amount} is caught first), turns deposits on
 *    with a 30-minute hold and sets the banquet deposit; it all stays;
 *  - a table's card: a deposit per guest from six guests, shown on its row;
 *  - a booking held for its deposit: the chip, until when the place waits,
 *    the reference, and "Paid" after asking once more confirms it. Deposits
 *    are only asked by the assistant, so this booking's deposit is served by
 *    the test;
 *  - a banquet request's deposit on its conversation: until when the link
 *    is valid, and "Paid" marks it paid (the request is served too);
 *  - on a phone the settings fit the screen.
 */

import type { APIRequestContext, Page } from "@playwright/test";

import type { Schema } from "../src/api/types";

import { nextSave } from "./support/autosave";
import { CONVERSATION_ID, openCard, serveCard } from "./support/conversation-card";
import { API_URL } from "./support/env";
import { expect, test } from "./support/fixtures";
import { cardWithLead, LEAD_ID, leadOf } from "./support/leads";
import { en } from "./support/messages";

const deposits = en.deposits;
const PAGE_ADDRESS = "https://pay.example.com/deposit?sum={amount}&ref={reference}";
const EVERY_DAY = [1, 2, 3, 4, 5, 6, 7].map((weekday) => ({ weekday, opens_at: 9 * 60, closes_at: 20 * 60 }));

function headersOf(token: string) {
  return { authorization: `Bearer ${token}` };
}

async function addTable(request: APIRequestContext, token: string, businessId: string, name: string): Promise<string> {
  const response = await request.post(`${API_URL}/v1/businesses/${businessId}/resources`, {
    data: { name, kind: "table", capacity: 8, schedule: EVERY_DAY },
    headers: headersOf(token),
  });
  expect(response.status(), await response.text()).toBe(201);
  return ((await response.json()) as { id: string }).id;
}

async function addPaymentPage(page: Page, label: string, address: string): Promise<void> {
  await page.getByLabel(deposits.pages.label).fill(label);
  await page.getByLabel(deposits.pages.address).fill(address);
  await page.getByRole("button", { name: deposits.pages.add }).click();
}

test("the owner adds a payment page, turns deposits on and sets the banquet deposit", async ({ page, owner }) => {
  await page.goto(`/b/${owner.businessId}/settings/deposits`);

  await expect(page.getByText(deposits.pages.empty)).toBeVisible();
  // A page that fills in the amount needs a place for it.
  await addPaymentPage(page, "Flitt", "https://pay.example.com/deposit");
  await expect(page.getByText(deposits.pages.refusals.templateInvalid)).toBeVisible();
  await page.getByLabel(deposits.pages.address).fill(PAGE_ADDRESS);
  await page.getByRole("button", { name: deposits.pages.add }).click();
  await expect(page.getByRole("status").filter({ hasText: deposits.pages.added })).toBeVisible();
  const row = page.getByRole("listitem").filter({ hasText: "Flitt" });
  await expect(row.getByText(deposits.pages.default, { exact: true })).toBeVisible();
  await expect(row.getByText("pay.example.com", { exact: false })).toBeVisible();

  const toggle = page.getByRole("switch", { name: deposits.settings.toggle });
  await expect(toggle).toHaveAttribute("aria-checked", "false");
  const switched = nextSave(page, "/deposit-settings");
  await toggle.click();
  await switched;
  const held = nextSave(page, "/deposit-settings");
  await page.getByLabel(deposits.settings.holdMinutes).fill("30");
  await page.getByLabel(deposits.settings.refundHours).focus();
  await held;

  // Out of range is not saved; the field says why once it is left.
  await page.getByLabel(deposits.settings.holdMinutes).fill("5");
  await page.getByLabel(deposits.settings.refundHours).focus();
  await expect(page.getByText(deposits.settings.errors.hold)).toBeVisible();
  await page.getByLabel(deposits.settings.holdMinutes).fill("30");

  await page.getByLabel(deposits.policy.rule, { exact: true }).selectOption("fixed");
  await page.getByLabel(deposits.policy.amount.replace("{currency}", "EUR")).fill("50");
  await page.getByRole("button", { name: deposits.policy.save }).click();
  await expect(page.getByRole("status").filter({ hasText: deposits.policy.saved })).toBeVisible();

  await page.reload();
  await expect(page.getByRole("switch", { name: deposits.settings.toggle })).toHaveAttribute("aria-checked", "true");
  await expect(page.getByLabel(deposits.settings.holdMinutes)).toHaveValue("30");
  await expect(page.getByLabel(deposits.policy.rule, { exact: true })).toHaveValue("fixed");
  await expect(page.getByLabel(deposits.policy.amount.replace("{currency}", "EUR"))).toHaveValue("50");
});

test("a table asks a deposit per guest from six guests", async ({ page, request, owner }) => {
  await addTable(request, owner.token, owner.businessId, "Terrace");
  await page.goto(`/b/${owner.businessId}/assistant/knowledge/resources`);

  const row = page.getByRole("listitem").filter({ hasText: "Terrace" });
  await row.getByRole("button", { name: `${en.common.edit}: Terrace` }).click();
  const dialog = page.getByRole("dialog");
  // No payment page yet: the card says where to add one.
  await expect(dialog.getByRole("link", { name: deposits.policy.openSettings })).toBeVisible();
  await dialog.getByLabel(deposits.policy.rule, { exact: true }).selectOption("per_guest");
  await dialog.getByLabel(deposits.policy.amountPerGuest.replace("{currency}", "EUR")).fill("20");
  await dialog.getByLabel(deposits.policy.minParty).fill("6");
  await dialog.getByRole("button", { name: deposits.policy.save }).click();
  await expect(page.getByRole("status").filter({ hasText: deposits.policy.saved })).toBeVisible();
  await dialog.getByRole("button", { name: en.common.cancel }).click();

  await expect(row.getByText(/20\.00/)).toBeVisible();
  await expect(row.getByText(new RegExp(deposits.policy.fromGuests.other.replace("{count}", "6")))).toBeVisible();
});

test("staff mark a held booking's deposit paid and the booking is confirmed", async ({ page, request, owner }) => {
  const tableId = await addTable(request, owner.token, owner.businessId, "Window");
  const tomorrow = new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString().slice(0, 10);
  const created = await request.post(`${API_URL}/v1/businesses/${owner.businessId}/bookings`, {
    data: { contact_name: "Nino Beridze", date: tomorrow, time: "11:00", party_size: 6, duration_minutes: 60, resource_id: tableId },
    headers: headersOf(owner.token),
  });
  expect(created.status(), await created.text()).toBe(201);
  const bookingId = ((await created.json()) as { booking: { id: string } }).booking.id;

  const depositId = "deposit_request_00000000-0000-5000-8000-000000000001";
  const holdExpiresAt = (Date.now() + 30 * 60 * 1000) * 1000;
  let isPaid = false;
  const request_: Schema<"DepositRequestView"> = {
    id: depositId,
    subject: "booking",
    booking_id: bookingId,
    contact_id: "contact_00000000-0000-5000-8000-000000000001",
    amount_minor: 12000,
    currency_code: "EUR",
    reference: "DK7Q3M9X",
    status: "awaiting",
    payment_link_label: "Flitt",
    source_channel: "web_chat",
    requested_at: Date.now() * 1000,
    hold_expires_at: holdExpiresAt,
  };
  const isBookingList = (url: URL) => /\/api\/backend\/v1\/businesses\/[^/]+\/bookings$/.test(url.pathname);
  await page.route(isBookingList, async (route) => {
    const response = await route.fetch();
    const body = (await response.json()) as { items: Schema<"BookingView">[] };
    const items = body.items.map((item) =>
      item.id === bookingId
        ? {
            ...item,
            status: isPaid ? ("confirmed" as const) : ("pending" as const),
            deposit: {
              request_id: depositId,
              amount_minor: 12000,
              currency_code: "EUR",
              status: isPaid ? ("paid" as const) : ("awaiting" as const),
              hold_expires_at: holdExpiresAt,
            },
          }
        : item,
    );
    await route.fulfill({ response, json: { ...body, items } });
  });
  await page.route(`**/api/backend/v1/businesses/*/deposits/${depositId}`, (route) =>
    route.fulfill({ json: { ...request_, status: isPaid ? "paid" : "awaiting" } }),
  );
  await page.route(`**/api/backend/v1/businesses/*/deposits/${depositId}/paid`, (route) => {
    isPaid = true;
    return route.fulfill({ json: { ...request_, status: "paid", paid_at: Date.now() * 1000 } });
  });

  await page.goto(`/b/${owner.businessId}/bookings`);
  const bookingRow = page.getByRole("button").filter({ hasText: "Nino Beridze" }).first();
  await expect(bookingRow.getByText(`${deposits.chip} · ${deposits.status.awaiting}`)).toBeVisible();
  await bookingRow.click();

  const details = page.getByRole("dialog");
  await expect(details.getByText(deposits.booking.reference.replace("{reference}", "DK7Q3M9X"))).toBeVisible();
  await details.getByRole("button", { name: deposits.booking.markPaid, exact: true }).click();
  const confirm = details.getByRole("group", { name: deposits.booking.confirmTitle });
  await expect(confirm).toBeVisible();
  await confirm.getByRole("button", { name: deposits.booking.confirm }).click();

  await expect(page.getByRole("status").filter({ hasText: deposits.booking.marked })).toBeVisible();
  await expect(details.getByText(`${deposits.chip} · ${deposits.status.paid}`)).toBeVisible();
  await expect(details.getByRole("button", { name: deposits.booking.markPaid, exact: true })).toHaveCount(0);
});

test("staff mark a banquet request's deposit paid in its conversation", async ({ page, owner }) => {
  const depositId = "deposit_request_00000000-0000-5000-8000-000000000002";
  const holdExpiresAt = (Date.now() + 60 * 60 * 1000) * 1000;
  let isPaid = false;
  const lead = (): Schema<"LeadListItem"> => ({
    ...leadOf(owner.businessId, "new"),
    conversation_id: CONVERSATION_ID,
    deposit: {
      request_id: depositId,
      amount_minor: 40000,
      currency_code: "EUR",
      status: isPaid ? "paid" : "awaiting",
      hold_expires_at: isPaid ? null : holdExpiresAt,
    },
  });
  const view: Schema<"DepositRequestView"> = {
    id: depositId,
    subject: "banquet",
    lead_id: LEAD_ID,
    contact_id: lead().contact_id,
    amount_minor: 40000,
    currency_code: "EUR",
    reference: "HK4R7T9W",
    status: "awaiting",
    payment_link_label: "Flitt",
    source_channel: "whatsapp",
    requested_at: Date.now() * 1000,
    hold_expires_at: holdExpiresAt,
  };
  await serveCard(page, owner.businessId, () => cardWithLead(owner.businessId, lead()));
  await page.route(`**/api/backend/v1/businesses/*/deposits/${depositId}`, (route) =>
    route.fulfill({ json: { ...view, status: isPaid ? "paid" : "awaiting" } }),
  );
  await page.route(`**/api/backend/v1/businesses/*/deposits/${depositId}/paid`, (route) => {
    isPaid = true;
    return route.fulfill({ json: { ...view, status: "paid", paid_at: Date.now() * 1000 } });
  });

  await openCard(page, owner.businessId);
  const request = page.getByRole("region", { name: en.inboxCard.work.request });
  await expect(request.getByText(`${deposits.chip} · ${deposits.status.awaiting}`)).toBeVisible();
  await expect(request.getByText(new RegExp(deposits.request.linkUntil.replace("{time}", ".+")))).toBeVisible();
  await expect(request.getByText(deposits.booking.reference.replace("{reference}", "HK4R7T9W"))).toBeVisible();
  await request.getByRole("button", { name: deposits.booking.markPaid, exact: true }).click();
  const confirm = request.getByRole("group", { name: deposits.booking.confirmTitle });
  await expect(confirm.getByText(/HK4R7T9W/)).toBeVisible();
  await confirm.getByRole("button", { name: deposits.booking.confirm }).click();

  await expect(page.getByRole("status").filter({ hasText: deposits.booking.marked })).toBeVisible();
  await expect(request.getByText(`${deposits.chip} · ${deposits.status.paid}`)).toBeVisible();
  await expect(request.getByRole("button", { name: deposits.booking.markPaid, exact: true })).toHaveCount(0);
});

test("on a phone Settings → Deposits fits the screen", async ({ page, owner }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(`/b/${owner.businessId}/settings/deposits`);

  await expect(page.getByRole("heading", { name: deposits.pages.title })).toBeVisible();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(0);
});
