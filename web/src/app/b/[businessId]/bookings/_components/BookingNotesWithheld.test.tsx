import { screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";

import type { BusinessView, CurrentUserView } from "@/api/types";
import { BusinessProvider } from "@/components/business/BusinessContext";
import { renderInLocale, textsIn } from "@/test/render";

import { bookingFixture } from "../_lib/bookingFixtures";
import { BookingDetails } from "./BookingList";

vi.mock("@/api/client", () => ({ api: { GET: vi.fn(), POST: vi.fn(), PATCH: vi.fn(), DELETE: vi.fn() } }));

const business = {
  id: "business_1",
  viewer_role: "agency",
  status: "live",
  currency_code: "EUR",
  timezone: "Asia/Tbilisi",
  niche_key: "restaurant",
} as unknown as BusinessView;
const me = { user: { id: "user_1", is_platform_admin: false } } as unknown as CurrentUserView;

function Viewer({ children }: { children: ReactNode }) {
  return (
    <BusinessProvider business={business} me={me}>
      {children}
    </BusinessProvider>
  );
}

describe("BookingDetails: a health note withheld from this viewer (PRIV-10)", () => {
  it.each(["en", "it"] as const)("says the note is for the owner and staff only (%s)", (locale) => {
    const { t } = textsIn(locale);
    renderInLocale(
      <Viewer>
        <BookingDetails booking={bookingFixture({ notes: null, is_health_note_withheld: true })} isStay={false} onDepositPaid={vi.fn()} />
      </Viewer>,
      { locale },
    );

    expect(screen.getByText(t("bookings.details.notesWithheld"))).toBeTruthy();
  });

  it("shows a note it may see as written", () => {
    const { t } = textsIn("en");
    renderInLocale(
      <Viewer>
        <BookingDetails booking={bookingFixture({ notes: "High chair" })} isStay={false} onDepositPaid={vi.fn()} />
      </Viewer>,
    );

    expect(screen.getByText("High chair")).toBeTruthy();
    expect(screen.queryByText(t("bookings.details.notesWithheld"))).toBeNull();
  });
});
