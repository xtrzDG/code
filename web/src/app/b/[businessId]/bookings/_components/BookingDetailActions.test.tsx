import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "@/api/client";
import type { BookingView } from "@/components/insights/types";
import { ok } from "@/test/fakeApi";
import { renderInLocale, textsIn } from "@/test/render";

import type { BookingsPage } from "../_lib/useBookingsPage";
import { BookingDetailActions } from "./BookingDetailActions";

vi.mock("@/api/client", () => ({ api: { GET: vi.fn(), POST: vi.fn(), PATCH: vi.fn(), DELETE: vi.fn() } }));

const ahead = {
  id: "booking_1",
  business_id: "business_1",
  status: "confirmed",
  date: "2099-05-10",
  end_date: "2099-05-10",
  time: "19:00",
  timezone: "Europe/Rome",
} as unknown as BookingView;
const page = { setDialog: vi.fn(), close: vi.fn(), openCancel: vi.fn(), runStatus: vi.fn() } as unknown as BookingsPage;

describe("BookingDetailActions: ending the guest's booking links", () => {
  beforeEach(() => {
    vi.mocked(api.POST).mockReset();
  });

  it.each(["en", "it"] as const)("ends the links sent so far from More and says so (%s)", async (locale) => {
    const { t } = textsIn(locale);
    vi.mocked(api.POST).mockImplementation((() => ok(undefined)) as never);
    renderInLocale(<BookingDetailActions booking={ahead} page={page} />, { locale });

    await userEvent.click(screen.getByRole("button", { name: t("bookings.actions.more") }));
    await userEvent.click(await screen.findByRole("menuitem", { name: t("bookings.actions.revokeLinks") }));

    await waitFor(() => expect(screen.getByText(t("bookings.actions.linksRevoked"))).toBeTruthy());
    expect(vi.mocked(api.POST).mock.calls[0]).toEqual([
      "/v1/businesses/{business_id}/bookings/{booking_id}/manage-links/revoke",
      { params: { path: { business_id: "business_1", booking_id: "booking_1" } } },
    ]);
  });

  it("offers nothing to end once the booking is over", () => {
    const { t } = textsIn("en");
    renderInLocale(<BookingDetailActions booking={{ ...ahead, status: "completed" }} page={page} />, { locale: "en" });

    // A finished booking has nothing under More: no menu at all.
    expect(screen.queryByRole("button", { name: t("bookings.actions.more") })).toBeNull();
    expect(screen.queryByText(t("bookings.actions.revokeLinks"))).toBeNull();
  });
});
