import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { BusinessView, CurrentUserView } from "@/api/types";
import { BusinessProvider } from "@/components/business/BusinessContext";
import { renderInLocale, textsIn } from "@/test/render";

import { TransferCard } from "./TransferCard";

const me = { user: { id: "user_1", is_platform_admin: false } } as unknown as CurrentUserView;

function renderCard(countryCode: string, locale: "en" | "it") {
  const business = {
    id: "business_1",
    country_code: countryCode,
    viewer_role: "owner",
    status: "live",
    currency_code: "EUR",
    timezone: "Europe/Rome",
  } as unknown as BusinessView;
  renderInLocale(
    <BusinessProvider business={business} me={me}>
      <TransferCard readiness="unconfirmed" phoneNumber="+393331234567" confirmedAt={null} switchRow={null} />
    </BusinessProvider>,
    { locale },
  );
}

/** What each business reads: the Italian law and its notice template in Italy only, "another EU country" in the EU only. */
const BUSINESSES = [
  { country: "IT", description: "descriptionItaly", numberRule: "numberRuleEu", template: "/help/staff-call-notice" },
  { country: "DE", description: "description", numberRule: "numberRuleEu", template: null },
  { country: "US", description: "description", numberRule: "numberRule", template: null },
] as const;

describe.each(BUSINESSES)("TransferCard of a business in $country", ({ country, description, numberRule, template }) => {
  it.each(["en", "it"] as const)("says what applies there (%s)", (locale) => {
    const { t } = textsIn(locale);
    renderCard(country, locale);

    expect(screen.getByText(t(`callSettings.transfers.${description}`))).toBeTruthy();
    expect(screen.getByText(t(`callSettings.transfers.${numberRule}`))).toBeTruthy();
    const link = screen.queryByRole("link", { name: t("callSettings.transfers.noticeTemplate") });
    expect(link?.getAttribute("href") ?? null).toBe(template);
    const page = document.body.textContent ?? "";
    if (country !== "IT") {
      expect(page).not.toMatch(/Workers' Statute|Statuto dei lavoratori/);
    }
    if (country === "US") {
      expect(page).not.toMatch(/another EU country|altro paese dell'UE/);
    }
  });
});
