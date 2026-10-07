import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "@/api/client";
import { queryCache } from "@/api/queryCache";
import type { CurrentUserView } from "@/api/types";
import { bookingFixture } from "@/app/b/[businessId]/bookings/_lib/bookingFixtures";
import { business } from "@/app/b/[businessId]/settings/_lib/settingsFixtures";
import { BusinessProvider } from "@/components/business/BusinessContext";
import type { BookingView } from "@/components/insights/types";
import type { Locale } from "@/i18n/config";
import { ok } from "@/test/fakeApi";
import { renderInLocale, textsIn } from "@/test/render";

import type { MoveTarget } from "./_lib/calendarTypes";
import { MoveMessageOffer } from "./MoveMessageOffer";
import { useCalendarMove } from "./useCalendarMove";

vi.mock("@/api/client", () => ({ api: { GET: vi.fn(), POST: vi.fn(), PATCH: vi.fn(), DELETE: vi.fn() } }));

const me = { user: { id: "user_owner", is_platform_admin: false } } as unknown as CurrentUserView;
const dinner = bookingFixture({ id: "booking_7", contact_name: "Nino", language: "en", time: "19:00", end_time: "21:00", resource_id: "res_window", resource_name: "Window" });
const terrace: MoveTarget = { resourceId: "res_terrace", resourceName: "Terrace", date: "2026-10-05", time: "21:00" };
const MOVED_TEXT = "Your table at Café Tbilisi is now on Monday, October 5 at 9:00 PM.";

/** The calendar's move as a drop does it, with the offer the calendar shows. */
function Calendar({ booking }: { booking: BookingView }) {
  const { move, message, dismissMessage } = useCalendarMove();
  return (
    <>
      <button type="button" data-testid="drop" onClick={() => void move(booking, terrace)} />
      <MoveMessageOffer message={message} onDismiss={dismissMessage} />
    </>
  );
}

/** The offer's title: the customer's name is its own element inside the sentence. */
const sentence = (text: string) => (_: string, element: Element | null) => element?.tagName === "P" && element.textContent === text;

function answerMoves(booking: BookingView) {
  vi.mocked(api.POST).mockImplementation(((_path: string, init: { body: { new_time: string; new_resource_id: string } }) => {
    const back = init.body.new_resource_id === dinner.resource_id;
    return ok({
      booking: { ...booking, resource_id: init.body.new_resource_id, time: init.body.new_time, resource_name: back ? "Window" : "Terrace" },
      confirmation_text: back ? "Back at 7:00 PM." : MOVED_TEXT,
    });
  }) as never);
}

async function dropIn(locale: Locale, booking: BookingView = dinner) {
  const user = userEvent.setup();
  answerMoves(booking);
  renderInLocale(
    <BusinessProvider business={business} me={me}>
      <Calendar booking={booking} />
    </BusinessProvider>,
    { locale },
  );
  await user.click(screen.getByTestId("drop"));
  return user;
}

describe("after a booking is moved on the calendar", () => {
  beforeEach(() => {
    queryCache.clear();
    vi.mocked(api.POST).mockReset();
  });

  it("offers the list's message about the new time, written in the customer's language", async () => {
    const { t } = textsIn("en");
    const user = await dropIn("en");

    const [, init] = vi.mocked(api.POST).mock.calls[0] as unknown as [string, { params: { query: { language: string } } }];
    expect(init.params.query.language).toBe("en");
    expect(await screen.findByText(sentence("Let Nino know the new time"))).toBeTruthy();
    expect(screen.getByText(t("bookingCalendar.move.tell.hint"))).toBeTruthy();

    await user.click(screen.getByRole("button", { name: t("bookingCalendar.move.tell.show") }));
    const dialog = screen.getByRole("dialog", { name: t("bookings.rescheduled") });
    expect(within(dialog).getByText(MOVED_TEXT)).toBeTruthy();
    expect(within(dialog).getByText(t("insights.customerMessage.title"))).toBeTruthy();

    await user.click(within(dialog).getByRole("button", { name: t("common.done") }));
    expect(screen.queryByText(sentence("Let Nino know the new time"))).toBeNull();
  });

  it("names nobody for a booking without a name and goes away on Close", async () => {
    const { t } = textsIn("de");
    const user = await dropIn("de", { ...dinner, contact_name: null });

    expect(await screen.findByText(t("bookingCalendar.move.tell.titleAnonymous"))).toBeTruthy();
    // The offer's Close, not the toast's.
    const close = screen.getAllByRole("button", { name: t("common.close") }).find((button) => !button.closest("[aria-live]"));
    await user.click(close as HTMLElement);
    expect(screen.queryByText(t("bookingCalendar.move.tell.titleAnonymous"))).toBeNull();
  });

  it("is withdrawn when the move is undone: the customer knows the old time", async () => {
    const { t } = textsIn("ru");
    const user = await dropIn("ru");
    expect(await screen.findByText(sentence("Nino ещё не знает новое время"))).toBeTruthy();

    await user.click(screen.getByRole("button", { name: t("common.undo") }));
    expect(await screen.findByText(t("bookingCalendar.move.undone"))).toBeTruthy();
    expect(vi.mocked(api.POST)).toHaveBeenCalledTimes(2);
    expect(screen.queryByText(sentence("Nino ещё не знает новое время"))).toBeNull();
  });

  it("reads right to left in Hebrew", async () => {
    await dropIn("he");
    expect(await screen.findByText(sentence("יש לעדכן את Nino בשעה החדשה"))).toBeTruthy();
  });
});
