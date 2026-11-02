import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { BusinessView, CurrentUserView } from "@/api/types";
import { BusinessProvider } from "@/components/business/BusinessContext";
import { renderInLocale, textsIn } from "@/test/render";

import { TransferCard } from "./TransferCard";

const business = {
  id: "business_1",
  viewer_role: "owner",
  status: "live",
  currency_code: "EUR",
  timezone: "Europe/Rome",
} as unknown as BusinessView;
const me = { user: { id: "user_1", is_platform_admin: false } } as unknown as CurrentUserView;

describe("TransferCard", () => {
  it.each(["en", "it"] as const)("links the notice template the staff must get first (%s)", (locale) => {
    renderInLocale(
      <BusinessProvider business={business} me={me}>
        <TransferCard readiness="unconfirmed" phoneNumber="+393331234567" confirmedAt={null} switchRow={null} />
      </BusinessProvider>,
      { locale },
    );

    const link = screen.getByRole("link", { name: textsIn(locale).t("callSettings.transfers.noticeTemplate") });
    expect(link.getAttribute("href")).toBe("/help/staff-call-notice");
  });
});
