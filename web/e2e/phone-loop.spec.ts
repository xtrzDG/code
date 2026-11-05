/**
 * The front desk on a phone (390×844), against the real API:
 *
 *  - Bookings opens on today's agenda; the first arrival starts in the top
 *    35% of the screen; "Arrived" waits for the start time; marking a
 *    booking arrived and pressing Undo in the toast gives it back its
 *    status, and the API agrees;
 *  - resolving a handoff and pressing Undo opens it again: the
 *    conversation waits for a person once more.
 *
 * The page's clock stands at 10:30 tomorrow in Berlin (the salon's zone), so
 * a booking at 10:00 has started and one at 12:00 has not, whatever time the
 * suite runs.
 */

import type { APIRequestContext } from "@playwright/test";

import { uniqueSuffix } from "./support/api";
import { signInAsDemoOwner, visitorAsksForPerson } from "./support/demo";
import { API_URL } from "./support/env";
import { expect, signInContext, test } from "./support/fixtures";
import { cardOf, waitingConversationOf } from "./support/inbox";
import { en } from "./support/messages";

test.describe.configure({ timeout: 120_000 });
test.use({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });

const BERLIN = "Europe/Berlin";
const EVERY_DAY = [1, 2, 3, 4, 5, 6, 7].map((weekday) => ({ weekday, opens_at: 9 * 60, closes_at: 20 * 60 }));

function headersOf(token: string) {
  return { authorization: `Bearer ${token}` };
}

/** "YYYY-MM-DD HH:MM" of an instant in Berlin. */
function berlinClock(instant: number): string {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: BERLIN,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  }).formatToParts(new Date(instant));
  const part = (type: string) => parts.find((item) => item.type === type)?.value ?? "";
  return `${part("year")}-${part("month")}-${part("day")} ${part("hour")}:${part("minute")}`;
}

/** The instant when Berlin's clocks show `date` `time`. */
function berlinInstant(date: string, time: string): Date {
  const asUtc = Date.parse(`${date}T${time}:00Z`);
  const shown = Date.parse(`${berlinClock(asUtc).replace(" ", "T")}:00Z`);
  return new Date(asUtc - (shown - asUtc));
}

/** A master who works every day from 9 to 20; returns their resource id. */
async function addMaster(request: APIRequestContext, token: string, businessId: string, name: string): Promise<string> {
  const response = await request.post(`${API_URL}/v1/businesses/${businessId}/resources`, {
    data: { name, kind: "staff", capacity: 1, schedule: EVERY_DAY },
    headers: headersOf(token),
  });
  expect(response.status(), await response.text()).toBe(201);
  return ((await response.json()) as { id: string }).id;
}

interface Booked {
  id: string;
  status: string;
}

/** A one-hour booking added by hand. */
async function bookByHand(
  request: APIRequestContext,
  token: string,
  businessId: string,
  booking: { name: string; date: string; time: string; resourceId: string },
): Promise<Booked> {
  const response = await request.post(`${API_URL}/v1/businesses/${businessId}/bookings`, {
    data: {
      contact_name: booking.name,
      date: booking.date,
      time: booking.time,
      party_size: 1,
      duration_minutes: 60,
      resource_id: booking.resourceId,
    },
    headers: headersOf(token),
  });
  expect(response.status(), await response.text()).toBe(201);
  return ((await response.json()) as { booking: Booked }).booking;
}

/** The booking's status as the API lists it. */
async function statusOf(request: APIRequestContext, token: string, businessId: string, date: string, bookingId: string): Promise<string> {
  const response = await request.get(`${API_URL}/v1/businesses/${businessId}/bookings`, {
    params: { from: date, to: date, limit: "50" },
    headers: headersOf(token),
  });
  expect(response.ok(), await response.text()).toBe(true);
  const items = ((await response.json()) as { items: Booked[] }).items;
  return items.find((item) => item.id === bookingId)?.status ?? "missing";
}

test("the phone opens on today's arrivals, marks one arrived and Undo gives it back", async ({ page, request, owner }) => {
  const tomorrow = berlinClock(Date.now() + 24 * 60 * 60 * 1000).slice(0, 10);
  const nino = await addMaster(request, owner.token, owner.businessId, "Nino");
  const lena = await addMaster(request, owner.token, owner.businessId, "Lena");
  const started = await bookByHand(request, owner.token, owner.businessId, {
    name: "Anna Schmidt",
    date: tomorrow,
    time: "10:00",
    resourceId: nino,
  });
  const later = await bookByHand(request, owner.token, owner.businessId, {
    name: "Lukas Weber",
    date: tomorrow,
    time: "12:00",
    resourceId: lena,
  });
  await page.clock.setFixedTime(berlinInstant(tomorrow, "10:30"));

  await page.goto(`/b/${owner.businessId}/bookings`);
  const agenda = page.getByRole("list", { name: en.bookings.today.label });
  await expect(agenda).toBeVisible();

  // The first arrival is in the top 35% of the screen.
  const startedCard = page.locator(`[data-booking-card="${started.id}"]`);
  await expect(page.locator("[data-booking-card]").first()).toHaveAttribute("data-booking-card", started.id);
  const box = await startedCard.boundingBox();
  expect(box, "the first card is laid out").not.toBeNull();
  expect(box!.y, "the first card's top").toBeLessThan(844 * 0.35);

  // 12:00 has not come yet: its buttons wait and say from when.
  const laterCard = page.locator(`[data-booking-card="${later.id}"]`);
  await expect(laterCard.getByRole("button", { name: en.bookings.today.arrived })).toBeDisabled();
  await expect(laterCard.getByText(en.bookings.today.availableAt.replace("{time}", "12:00 PM"))).toBeVisible();

  // Arrived, then Undo in the toast.
  await startedCard.getByRole("button", { name: en.bookings.today.arrived }).click();
  await expect(startedCard.getByRole("button", { name: en.bookings.today.arrived })).toHaveCount(0);
  await expect.poll(() => statusOf(request, owner.token, owner.businessId, tomorrow, started.id)).toBe("completed");
  const toast = page.getByRole("status").filter({ hasText: en.bookings.today.markedArrived.replace("{name}", "Anna Schmidt") });
  await toast.getByRole("button", { name: en.common.undo }).click();

  await expect(startedCard.getByRole("button", { name: en.bookings.today.arrived })).toBeEnabled();
  await expect.poll(() => statusOf(request, owner.token, owner.businessId, tomorrow, started.id)).toBe(started.status);
});

test("Undo after Resolve opens the handoff again", async ({ page, request }) => {
  const owner = await signInAsDemoOwner(request);
  await signInContext(page.context(), owner.token);
  const visitor = await visitorAsksForPerson(request, owner.businessId, `Phone loop visitor ${uniqueSuffix()}`);
  const conversationId = await waitingConversationOf(request, owner.token, owner.businessId, visitor.name);

  await page.goto(`/b/${owner.businessId}/inbox/${conversationId}`);
  const resolve = page.getByRole("button", { name: en.inboxCard.actions.resolve, exact: true });
  await expect(resolve).toBeInViewport();
  await resolve.click();
  const confirm = page.getByRole("alertdialog").or(page.getByRole("dialog"));
  await confirm.getByRole("button", { name: en.inboxCard.resolveConfirm.confirm, exact: true }).click();
  await expect(resolve).toHaveCount(0);
  const isWaiting = async () =>
    (await cardOf(request, owner.token, owner.businessId, conversationId)).handoffs.some((handoff) => handoff.status !== "resolved");
  await expect.poll(isWaiting).toBe(false);

  const toast = page.getByRole("status").filter({ hasText: en.inboxCard.resolved });
  await toast.getByRole("button", { name: en.common.undo }).click();
  await expect(page.getByText(en.inboxCard.reopened)).toBeVisible();
  await expect(resolve).toBeVisible();
  await expect.poll(isWaiting).toBe(true);
  expect(await waitingConversationOf(request, owner.token, owner.businessId, visitor.name)).toBe(conversationId);
});
