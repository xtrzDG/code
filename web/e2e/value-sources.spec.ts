/**
 * Where owners read the value: Reports → "Where customers came from" (the
 * demo restaurant's conversations carry the share card's tags, the line
 * called and ads), the Overview card "What customers ask about" (topics
 * grouped by the rehearsal model when the demo is seeded), the source chip
 * of the inbox, and where the summaries arrive (a WhatsApp number checked
 * in the form, the API's refusal in the owner's language).
 */

import { API_URL } from "./support/env";
import { expect, signInContext, test } from "./support/fixtures";
import { signInAsDemoOwner } from "./support/demo";
import { en } from "./support/messages";

test.describe.configure({ timeout: 120_000 });

interface SourceRow {
  kind: "tagged" | "untagged" | "other";
  acquisition_source?: string | null;
  conversation_count: number;
  booking_count: number;
}

test("the owner reads where customers came from, per source and in total", async ({ page, context, request }) => {
  const owner = await signInAsDemoOwner(request);
  await signInContext(context, owner.token);
  const stored = await request.get(`${API_URL}/v1/businesses/${owner.businessId}/value/sources?period=30d`, {
    headers: { authorization: `Bearer ${owner.token}` },
  });
  expect(stored.status(), await stored.text()).toBe(200);
  const rows = ((await stored.json()) as { rows: SourceRow[] }).rows;
  const conversations = rows.reduce((sum, row) => sum + row.conversation_count, 0);
  expect(rows.some((row) => row.acquisition_source === "table"), "the demo has table-card conversations").toBe(true);

  await page.goto(`/b/${owner.businessId}/overview/reports`);
  const card = page.getByRole("region", { name: en.sources.title });
  await expect(card).toBeVisible();
  const table = card.getByRole("table");
  await expect(table.getByRole("columnheader", { name: en.sources.columns.source })).toBeVisible();
  await expect(table.getByRole("columnheader", { name: en.sources.columns.conversations })).toBeVisible();
  await expect(table.getByRole("columnheader", { name: en.sources.columns.value })).toBeVisible();

  // The share card's places read by their names, the raw tag under them.
  const tableCard = table.getByRole("rowheader", { name: new RegExp(en.share.sources.table) });
  await expect(tableCard).toBeVisible();
  await expect(tableCard.getByText(/^table · /)).toBeVisible();
  // The line called reads as a number; conversations without a tag by their channel.
  await expect(table.getByRole("rowheader", { name: /Call to \+/ }).first()).toBeVisible();
  await expect(table.getByRole("rowheader", { name: new RegExp(en.sources.untagged) }).first()).toBeVisible();

  // The total row adds the rows up.
  const total = table.getByRole("row", { name: new RegExp(`^${en.sources.total}`) });
  await expect(total.getByRole("cell").first()).toHaveText(String(conversations));

  // Another period loads its own rows.
  const week = page.waitForResponse((response) => /\/value\/sources\?period=7d/.test(response.url()) && response.ok());
  await card.getByText(en.sources.periods["7d"], { exact: true }).click();
  await week;
  await expect(card.getByRole("radio", { name: en.sources.periods["7d"] })).toBeChecked();
  await expect(table.getByRole("row", { name: new RegExp(`^${en.sources.total}`) })).toBeVisible();
});

test("the overview weighs the value against the plan's trial, shows what customers ask about, and the inbox where they came from", async ({
  page,
  context,
  request,
}) => {
  const owner = await signInAsDemoOwner(request);
  await signInContext(context, owner.token);
  // Restaurant tables have no price of their own: the period's bookings here are a salon's services.
  await page.route(/\/api\/backend\/v1\/businesses\/[^/]+\/dashboard\?/, async (route) => {
    const response = await route.fetch();
    const stats = (await response.json()) as Record<string, unknown>;
    await route.fulfill({ response, json: { ...stats, booked_value: [{ currency_code: "GEL", booking_count: 3, value_minor: 45_000 }] } });
  });

  await page.goto(`/b/${owner.businessId}/overview`);
  // The demo restaurant is in its free trial: the plan costs nothing yet, so the hero says
  // what it will cost after the trial instead of how many times the plan the money is.
  const [before] = en.value.hero.trialUntil.split("{date}");
  await expect(page.getByText(new RegExp(`^${escapeRegExp(before!)}.+`))).toBeVisible();
  const [multiple] = en.value.hero.returnMultiple.split("{multiple}");
  await expect(page.getByText(new RegExp(`^${escapeRegExp(multiple!)}[\\d.,]+`))).toHaveCount(0);
  // Bookings at their own prices have a tile of their own, counting every booking.
  await expect(page.getByText(en.dashboard.kpi.bookedValue, { exact: true })).toBeVisible();
  await expect(page.getByText(`3 bookings at their own prices · ${en.dashboard.kpi.bookedValueScope}`)).toBeVisible();

  const topics = page.getByRole("region", { name: en.topics.title });
  await expect(topics).toBeVisible();
  await expect(topics.getByRole("listitem").first()).toBeVisible();
  await expect(topics.getByText(/conversations?$/).first()).toBeVisible();
  const answer = topics.getByRole("link", { name: new RegExp(`^${en.topics.addAnswer}`) });
  if ((await answer.count()) > 0) {
    await answer.first().click();
    await expect(page).toHaveURL(new RegExp(`/b/${owner.businessId}/assistant/knowledge/questions$`));
  }

  // Where a customer came from is in the row's details: the card beside the row under the pointer.
  await page.goto(`/b/${owner.businessId}/inbox?view=all`);
  const fromSource = page.locator("[data-inbox-row]").filter({ hasText: en.inboxTriage.details.source }).first();
  await fromSource.locator("a").first().hover();
  await expect(page.locator("[data-row-hint]").getByText(en.inboxTriage.details.source, { exact: true })).toBeVisible();
});

test("a WhatsApp number is checked before it is saved, and a refusal reads in the owner's language", async ({ page, owner, consoleErrors }) => {
  // The platform's WhatsApp number is not set up in the suite: the API refuses the channel.
  consoleErrors.allow(/Failed to load resource: the server responded with a status of 422/);
  await page.route(/\/api\/backend\/v1\/businesses\/[^/]+\/digest-preferences$/, async (route) => {
    if (route.request().method() !== "GET") {
      await route.continue();
      return;
    }
    const response = await route.fetch();
    const view = (await response.json()) as Record<string, unknown>;
    await route.fulfill({ response, json: { ...view, is_whatsapp_ready: true } });
  });
  await page.goto(`/b/${owner.businessId}/overview/reports`);

  const channels = page.getByRole("region", { name: en.digestChannels.title });
  await expect(channels.getByRole("switch", { name: en.digestChannels.push })).toHaveAttribute("aria-checked", "true");
  const whatsapp = channels.getByRole("switch", { name: en.digestChannels.whatsapp });
  await expect(whatsapp).toHaveAttribute("aria-checked", "false");
  await whatsapp.click();

  // No number yet: the field opens and the switch waits for one.
  const number = channels.getByLabel(en.digestChannels.whatsappNumber);
  await number.fill("555 12 34");
  await channels.getByRole("button", { name: en.digestChannels.save }).click();
  await expect(channels.getByText(en.digestChannels.invalidNumber)).toBeVisible();

  await number.fill("+995 555 12 34 56");
  const saved = page.waitForResponse((response) => /digest-preferences$/.test(response.url()) && response.request().method() === "PUT");
  await channels.getByRole("button", { name: en.digestChannels.save }).click();
  expect((await saved).status()).toBe(422);
  await expect(page.getByText(en.digestChannels.refusals.whatsappNotAvailable)).toBeVisible();
  await expect(whatsapp).toHaveAttribute("aria-checked", "false");
});

function escapeRegExp(text: string): string {
  return text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}
