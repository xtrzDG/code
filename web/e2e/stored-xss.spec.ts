/**
 * Stored XSS against the real API (INP-02): markup and javascript: links a
 * visitor writes in the website chat, a customer's name typed with a
 * booking and a knowledge text are shown as text in the cabinet (the
 * conversation, the customer's page, the customer list, the knowledge
 * base), never as elements, and nothing in them runs.
 */

import type { APIRequestContext, Page } from "@playwright/test";

import { uniqueSuffix } from "./support/api";
import { signInAsDemoOwner } from "./support/demo";
import { API_URL } from "./support/env";
import { expect, signInContext, test } from "./support/fixtures";
import { waitingConversationOf } from "./support/inbox";
import { en } from "./support/messages";

test.describe.configure({ timeout: 120_000 });

/** Set by any payload that runs. */
const MARK = "__awXss";
const IMAGE = `<img src=x onerror="window.${MARK}=1">`;
const SCRIPT_LINK = `<a href="javascript:window.${MARK}=2">open</a>`;
const MARKDOWN_LINK = `[open](javascript:window.${MARK}=3)`;
const SVG = `<svg onload="window.${MARK}=4"></svg>`;
const PAYLOADS = [IMAGE, SCRIPT_LINK, MARKDOWN_LINK, SVG];
const EVERY_DAY = [1, 2, 3, 4, 5, 6, 7].map((weekday) => ({ weekday, opens_at: 9 * 60, closes_at: 20 * 60 }));

function headersOf(token: string) {
  return { authorization: `Bearer ${token}` };
}

/** Nothing planted became an element, and nothing ran. */
async function expectNothingRan(page: Page): Promise<void> {
  await expect(page.locator('img[src="x"], [onerror], [onload]')).toHaveCount(0);
  await expect(page.locator('a[href^="javascript:" i]')).toHaveCount(0);
  expect(await page.evaluate((mark) => (window as unknown as Record<string, unknown>)[mark], MARK)).toBeUndefined();
}

/** A visitor of the website chat asks for a person with markup in the message. */
async function visitorPlantsMarkup(request: APIRequestContext, businessId: string, name: string): Promise<string> {
  const sessionKey = `e2e_${uniqueSuffix()}_xss`;
  const url = `${API_URL}/v1/widget/${businessId}/messages`;
  const text = `Can I talk to a manager? ${PAYLOADS.join(" ")}`;
  const sent = await request.post(url, { data: { session_key: sessionKey, text, contact_name: name } });
  expect(sent.status(), await sent.text()).toBe(202);
  await expect
    .poll(
      async () => {
        const poll = await request.get(url, { headers: { "X-Widget-Session-Key": sessionKey } });
        return poll.ok() && ((await poll.json()) as { is_handed_off: boolean }).is_handed_off;
      },
      { message: "the worker handed the chat to a person", timeout: 15_000 },
    )
    .toBe(true);
  return text;
}

/** A customer added with a booking by hand, whose name carries markup; returns their contact id. */
async function customerNamed(request: APIRequestContext, token: string, businessId: string, name: string, tag: string): Promise<string> {
  const master = await request.post(`${API_URL}/v1/businesses/${businessId}/resources`, {
    data: { name: "Lena", kind: "staff", capacity: 1, schedule: EVERY_DAY },
    headers: headersOf(token),
  });
  expect(master.status(), await master.text()).toBe(201);
  const day = new Date(Date.now() + 3 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10);
  const booked = await request.post(`${API_URL}/v1/businesses/${businessId}/bookings`, {
    data: {
      contact_name: name,
      contact_phone_number: "+390612345678",
      date: day,
      time: "12:00",
      party_size: 1,
      duration_minutes: 60,
      resource_id: ((await master.json()) as { id: string }).id,
    },
    headers: headersOf(token),
  });
  expect(booked.status(), await booked.text()).toBe(201);
  const listed = await request.get(`${API_URL}/v1/businesses/${businessId}/contacts`, {
    params: { search: tag },
    headers: headersOf(token),
  });
  expect(listed.ok(), await listed.text()).toBe(true);
  const items = ((await listed.json()) as { items: { id: string; name?: string | null }[] }).items;
  const contact = items.find((item) => item.name === name);
  expect(contact, "the booking made its guest a customer, name as typed").toBeDefined();
  return contact!.id;
}

test("markup a visitor writes stays text in the conversation and on the customer's page", async ({ page, request }) => {
  const owner = await signInAsDemoOwner(request);
  await signInContext(page.context(), owner.token);
  const name = `Planted visitor ${uniqueSuffix()}`;
  const text = await visitorPlantsMarkup(request, owner.businessId, name);
  const conversationId = await waitingConversationOf(request, owner.token, owner.businessId, name);

  await page.goto(`/b/${owner.businessId}/inbox/${conversationId}`);
  const transcript = page.getByRole("region", { name: en.conversations.transcript });
  await expect(transcript).toContainText(text);
  await expectNothingRan(page);

  await page.getByRole("link", { name: en.customers.standing.open.replace("{line}", en.customers.standing.new) }).click();
  await expect(page).toHaveURL(new RegExp(`/b/${owner.businessId}/customers/contact_`));
  await expect(page.getByRole("heading", { name }).first()).toBeVisible();
  await expectNothingRan(page);
});

test("markup in a customer's name and in a knowledge text stays text", async ({ page, request, owner }) => {
  const tag = uniqueSuffix();
  const name = `Eve ${IMAGE} ${tag}`;
  const contactId = await customerNamed(request, owner.token, owner.businessId, name, tag);
  const created = await request.post(`${API_URL}/v1/businesses/${owner.businessId}/knowledge`, {
    headers: headersOf(owner.token),
    data: { kind: "faq", title: `Parking ${tag}`, body: `Yes, in the yard. ${PAYLOADS.join(" ")}` },
  });
  expect(created.status(), await created.text()).toBe(201);

  await page.goto(`/b/${owner.businessId}/customers/${contactId}`);
  await expect(page.getByRole("heading", { name }).first()).toBeVisible();
  await expectNothingRan(page);

  await page.goto(`/b/${owner.businessId}/customers`);
  await expect(page.getByRole("link", { name: new RegExp(tag) }).first()).toContainText(IMAGE);
  await expectNothingRan(page);

  await page.goto(`/b/${owner.businessId}/assistant/knowledge`);
  await expect(page.getByText(`Parking ${tag}`).first()).toBeVisible();
  await expect(page.getByText(SCRIPT_LINK, { exact: false }).first()).toBeVisible();
  await expectNothingRan(page);
});
