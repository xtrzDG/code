/**
 * Services in the cabinet: the owner adds a 45-minute service performed by
 * Nino in the knowledge base, books it by hand (its length filled in, only
 * Nino offered, its value shown) and sees the service and its value in the
 * bookings list; Nino's resource lists the service. The demo salon's
 * bookings read "1 клиент", never "1 гость".
 */

import type { APIRequestContext } from "@playwright/test";

import { API_URL, WEB_URL } from "./support/env";
import { signInAsDemoOwner } from "./support/demo";
import { expect, signInContext, test } from "./support/fixtures";
import { en, ru } from "./support/messages";
import { waitForNetworkQuiet } from "./support/network";

test.describe.configure({ timeout: 120_000 });

const EVERY_DAY = [1, 2, 3, 4, 5, 6, 7].map((weekday) => ({ weekday, opens_at: 9 * 60, closes_at: 20 * 60 }));

/** A master who works every day from 9 to 20, so the booking fits whatever day the suite runs. */
async function addMaster(request: APIRequestContext, token: string, businessId: string, name: string): Promise<void> {
  const response = await request.post(`${API_URL}/v1/businesses/${businessId}/resources`, {
    data: { name, kind: "staff", capacity: 1, schedule: EVERY_DAY },
    headers: { authorization: `Bearer ${token}` },
  });
  expect(response.status(), await response.text()).toBe(201);
}

/** Tomorrow in Berlin as YYYY-MM-DD (the salon's time zone). */
function tomorrowInBerlin(): string {
  const parts = new Intl.DateTimeFormat("en-CA", { timeZone: "Europe/Berlin", year: "numeric", month: "2-digit", day: "2-digit" })
    .formatToParts(new Date(Date.now() + 24 * 60 * 60 * 1000));
  const part = (type: string) => parts.find((item) => item.type === type)?.value ?? "";
  return `${part("year")}-${part("month")}-${part("day")}`;
}

test("a 45-minute service performed by Nino is booked by hand and its value shows in the list", async ({ page, request, owner }) => {
  await addMaster(request, owner.token, owner.businessId, "Nino");
  await addMaster(request, owner.token, owner.businessId, "Lena");

  // The service: 45 minutes, a 10-minute break, €35, performed by Nino only.
  await page.goto(`/b/${owner.businessId}/assistant/knowledge`);
  await page.getByRole("button", { name: en.knowledge.items.add }).first().click();
  const editor = page.getByRole("dialog", { name: en.knowledge.form.createTitle });
  await editor.getByLabel(en.knowledge.form.kind).selectOption("service");
  await editor.getByRole("textbox", { name: en.knowledge.form.title, exact: true }).fill("Ladies' haircut");
  await editor.getByLabel(en.knowledge.form.price.replace("{currency}", "EUR")).fill("35");
  await editor.getByLabel(en.knowledge.form.duration).fill("45");
  await editor.getByLabel(en.knowledge.offer.buffer).fill("10");
  const performers = editor.getByRole("group", { name: new RegExp(en.knowledge.offer.performers) });
  await performers.getByRole("checkbox", { name: /Nino/ }).check();
  await editor.getByRole("button", { name: en.knowledge.form.add, exact: true }).click();
  await expect(page.getByText(en.knowledge.form.created)).toBeVisible();
  await expect(page.getByText(en.knowledge.offer.performedBy.replace("{names}", "Nino"))).toBeVisible();

  // Nino's resource lists the service from the other side.
  await page.goto(`/b/${owner.businessId}/assistant/knowledge/resources`);
  await expect(page.getByText(en.knowledge.resources.servesValue.replace("{names}", "Ladies' haircut"))).toBeVisible();

  // The manual booking: the service fills in its length and offers only Nino; the value shows before booking.
  await page.goto(`/b/${owner.businessId}/bookings`);
  await waitForNetworkQuiet(page);
  await page.getByRole("button", { name: en.bookings.newBooking }).first().click();
  const form = page.getByRole("dialog", { name: en.bookings.form.title });
  await form.getByLabel(en.bookings.form.contactName).fill("Mariam Beridze");
  await form.getByLabel(en.bookings.form.service, { exact: true }).selectOption({ label: "Ladies' haircut · 45 min · €35.00" });
  await expect(form.getByLabel(en.bookings.form.duration)).toHaveValue("45");
  const master = form.getByLabel("Master");
  await expect(master.getByRole("option")).toHaveText([en.bookings.form.anyResource, "Nino"]);
  await expect(form.getByText(en.bookings.form.performersOnly)).toBeVisible();
  await expect(form.getByLabel(en.bookings.partyLabel.clients)).toHaveValue("1");
  await form.getByLabel(en.bookings.form.date).fill(tomorrowInBerlin());
  await form.getByLabel(new RegExp(`^${en.bookings.form.time}\\*?$`)).fill("10:00");
  await expect(form.getByText("€35.00", { exact: true })).toBeVisible();
  await form.getByRole("button", { name: en.bookings.form.submit }).click();

  // The confirmation for the customer, then the list: the service, Nino, "1 client" and the value.
  await expect(page.getByRole("dialog", { name: en.bookings.created })).toBeVisible();
  await page.keyboard.press("Escape");
  const row = page.getByRole("button", { name: /Mariam Beridze/ });
  await expect(row).toBeVisible();
  await expect(row).toContainText("Ladies' haircut");
  await expect(row).toContainText("1 client");
  await expect(row).toContainText("Nino");
  await expect(row).toContainText("€35.00");
  await expect(row).toContainText("10:00");
  await expect(row).toContainText("10:45");

  // The booking's card names the service and its value.
  await row.click();
  const card = page.getByRole("dialog", { name: "Mariam Beridze" });
  await expect(card.getByText(en.bookings.details.service, { exact: true })).toBeVisible();
  await expect(card.getByText(en.bookings.details.value, { exact: true })).toBeVisible();
  await expect(card.getByText("€35.00", { exact: true })).toBeVisible();
});

test("the demo salon counts clients, not guests", async ({ page, context, request }) => {
  const demo = await signInAsDemoOwner(request);
  const listed = await request.get(`${API_URL}/v1/businesses`, { headers: { authorization: `Bearer ${demo.token}` } });
  const salon = ((await listed.json()) as { id: string; niche_key: string }[]).find((business) => business.niche_key === "beauty_salon");
  expect(salon, "the demo salon is seeded").toBeDefined();
  await signInContext(context, demo.token);
  await context.addCookies([{ name: "aw_locale", value: "ru", url: WEB_URL, sameSite: "Lax" }]);

  await page.goto(`/b/${salon!.id}/bookings?range=upcoming`);
  await waitForNetworkQuiet(page);
  const list = page.getByRole("main");
  const oneClient = (ru.bookings.party.clients.one ?? ru.bookings.party.clients.other).replace("{count}", "1");
  await expect(list.getByText(new RegExp(oneClient)).first()).toBeVisible();
  await expect(list.getByText(/гост(ь|я|ей)/)).toHaveCount(0);
});
