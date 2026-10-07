import { fireEvent, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "@/api/client";
import type { Schema } from "@/api/types";
import { BOOKING_DATE_TEXTS } from "@/lib/bookingPage/dateTexts";
import { bookingPageTexts } from "@/lib/bookingPage/texts";
import { answerGet, ok } from "@/test/fakeApi";
import { renderInLocale, textsIn } from "@/test/render";

import { ReschedulePanel } from "./ReschedulePanel";

vi.mock("@/api/client", () => ({ api: { GET: vi.fn(), POST: vi.fn(), PATCH: vi.fn(), DELETE: vi.fn() } }));

const SLOTS = "/v1/public/bookings/{token}/slots";

const view = {
  token: "t".repeat(48),
  business_name: "Mtsvane Ezo",
  booking_unit: "time_slot",
  status: "confirmed",
  date: "2026-10-08",
  end_date: "2026-10-08",
  time: "19:00",
  end_time: "21:00",
  timezone: "Asia/Tbilisi",
  language: "tr",
  party_size: 2,
  can_cancel: true,
  can_reschedule: true,
  is_over: false,
} as Schema<"ManagedBookingView">;

function serveSlots() {
  answerGet((path, init) => {
    if (path !== SLOTS) throw new Error(`unexpected GET ${path}`);
    const date = init.params?.query?.date ?? "";
    return ok({ booking_unit: "time_slot", date, is_open_on_date: true, is_stay_available: false, times: ["18:00", "19:00", "20:30"], timezone: view.timezone });
  });
}

/** The dates the panel asked free times for. */
function askedDates(): string[] {
  return vi.mocked(api.GET).mock.calls.map((call) => (call[1] as { params: { query: { date: string } } }).params.query.date);
}

function renderPanel(language: string) {
  const onMoved = vi.fn();
  renderInLocale(
    <ReschedulePanel
      id="bp-move"
      view={{ ...view, language }}
      texts={bookingPageTexts(language)}
      language={language}
      onMoved={onMoved}
      onProblem={() => undefined}
      onClose={() => undefined}
    />,
    // The cabinet's own language stays English: the panel speaks the guest's.
    { locale: "en" },
  );
  return { onMoved, panel: screen.getByRole("region", { name: bookingPageTexts(language).newTime }) };
}

describe("ReschedulePanel: a guest picks another free time", () => {
  beforeEach(() => {
    vi.useFakeTimers({ toFake: ["Date"], now: new Date("2026-10-06T08:00:00Z") });
    serveSlots();
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it("reads and picks the date in the guest's language, not the cabinet's", async () => {
    const user = userEvent.setup();
    const turkish = BOOKING_DATE_TEXTS.tr!;
    const { panel } = renderPanel("tr");

    const field = within(panel).getByRole("combobox", { name: bookingPageTexts("tr").date });
    expect((field as HTMLInputElement).value).toBe("8 Eki 2026");
    expect(within(panel).queryByRole("button", { name: textsIn("en").t("formFields.date.open") })).toBeNull();

    await user.click(within(panel).getByRole("button", { name: turkish.open }));
    const calendar = within(panel).getByRole("dialog", { name: turkish.calendar });
    expect(within(calendar).getByRole("button", { name: turkish.nextMonth })).toBeTruthy();
    expect(within(calendar).getByRole("button", { name: turkish.today })).toBeTruthy();
    // Days before the business's today cannot be picked.
    expect(within(calendar).getByRole("button", { name: /^5 Ekim 2026/ }).getAttribute("aria-disabled")).toBe("true");

    await user.click(within(calendar).getByRole("button", { name: /^9 Ekim 2026/ }));
    expect((field as HTMLInputElement).value).toBe("9 Eki 2026");
    expect(askedDates()).toEqual(["2026-10-08", "2026-10-09"]);
  });

  it("moves the booking to a free time of the chosen day", async () => {
    const user = userEvent.setup();
    const texts = bookingPageTexts("en");
    const { panel, onMoved } = renderPanel("en");
    vi.mocked(api.POST).mockImplementation((() => ok({ ...view, date: "2026-10-10", time: "20:30" })) as never);

    const field = within(panel).getByRole("combobox", { name: texts.date });
    fireEvent.change(field, { target: { value: "Oct 10, 2026" } });
    const times = await within(panel).findByRole("group", { name: texts.freeTimes });
    await user.click(within(times).getByRole("button", { name: "8:30 PM" }));
    await user.click(within(panel).getByRole("button", { name: /^Move to Saturday, October 10, 2026, 8:30 PM$/ }));

    expect(vi.mocked(api.POST).mock.calls[0]?.[1]).toMatchObject({ body: { date: "2026-10-10", time: "20:30" } });
    expect(onMoved).toHaveBeenCalledWith(expect.objectContaining({ date: "2026-10-10" }));
  });

  it("says so for a date before today and asks for no free times", async () => {
    const texts = bookingPageTexts("en");
    const { panel } = renderPanel("en");
    await within(panel).findByRole("group", { name: texts.freeTimes });

    const field = within(panel).getByRole("combobox", { name: texts.date });
    fireEvent.change(field, { target: { value: "Oct 1, 2026" } });

    expect(within(panel).getByText(BOOKING_DATE_TEXTS.en!.pastDate)).toBeTruthy();
    expect(field.getAttribute("aria-invalid")).toBe("true");
    expect(within(panel).queryByRole("group", { name: texts.freeTimes })).toBeNull();
    expect(within(panel).getByRole("button", { name: /^Move to / }).hasAttribute("disabled")).toBe(true);
    expect(askedDates()).toEqual(["2026-10-08"]);
  });

  it("speaks Hebrew in a Hebrew guest's calendar, its week from Sunday", async () => {
    const user = userEvent.setup();
    const hebrew = BOOKING_DATE_TEXTS.he!;
    const { panel } = renderPanel("he");

    await user.click(within(panel).getByRole("button", { name: hebrew.open }));
    const calendar = within(panel).getByRole("dialog", { name: hebrew.calendar });
    expect(within(calendar).getByRole("button", { name: hebrew.previousMonth })).toBeTruthy();
    const firstColumn = within(calendar).getAllByRole("columnheader")[0];
    expect(firstColumn?.getAttribute("abbr")).toBe("יום ראשון");
  });
});
