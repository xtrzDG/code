import { screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { BusinessView, CurrentUserView } from "@/api/types";
import type { BookingView } from "@/components/insights/types";
import { BusinessProvider } from "@/components/business/BusinessContext";
import { renderInLocale, textsIn } from "@/test/render";

import { bookingFixture } from "../_lib/bookingFixtures";
import { BookingDetails } from "./BookingList";

vi.mock("@/api/client", () => ({ api: { GET: vi.fn(), POST: vi.fn(), PATCH: vi.fn(), DELETE: vi.fn() } }));

const agency = { id: "business_1", viewer_role: "agency", currency_code: "EUR", timezone: "Asia/Tbilisi" } as unknown as BusinessView;
const viewer = { user: { id: "user_2", is_platform_admin: false } } as unknown as CurrentUserView;

/** The booking's details as an agency helper sees them. */
function showDetails(booking: BookingView, locale: "en" | "it" = "en") {
  const details = <BookingDetails booking={booking} isStay={false} onDepositPaid={vi.fn()} />;
  return renderInLocale(
    <BusinessProvider business={agency} me={viewer}>
      {details}
    </BusinessProvider>,
    { locale },
  );
}

describe("BookingDetails: a health note withheld from this viewer (PRIV-10)", () => {
  it.each(["en", "it"] as const)("says the note is for the owner and staff only (%s)", (locale) => {
    const { t } = textsIn(locale);
    showDetails(bookingFixture({ notes: null, is_health_note_withheld: true }), locale);

    expect(screen.getByText(t("bookings.details.notesWithheld"))).toBeTruthy();
  });

  it("shows a note it may see as written", () => {
    const { t } = textsIn("en");
    showDetails(bookingFixture({ notes: "High chair" }));

    expect(screen.getByText("High chair")).toBeTruthy();
    expect(screen.queryByText(t("bookings.details.notesWithheld"))).toBeNull();
  });
});
