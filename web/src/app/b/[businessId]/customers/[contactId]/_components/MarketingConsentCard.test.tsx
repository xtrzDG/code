import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "@/api/client";
import type { BusinessView, CurrentUserView, Schema } from "@/api/types";
import type { Query } from "@/api/useQuery";
import { BusinessProvider } from "@/components/business/BusinessContext";
import type { Locale } from "@/i18n/config";
import { ok } from "@/test/fakeApi";
import { marketingConsentTexts } from "@/app/r/[token]/_components/marketingConsent/consentTexts";
import { renderInLocale, textsIn } from "@/test/render";

import type { CustomerDetail } from "../../_lib/customerModel";
import { MarketingConsentCard } from "./MarketingConsentCard";

vi.mock("@/api/client", () => ({ api: { GET: vi.fn(), POST: vi.fn(), PATCH: vi.fn(), PUT: vi.fn(), DELETE: vi.fn() } }));

type Consent = Schema<"MarketingConsentView">;

const me = { user: { id: "user_staff", is_platform_admin: false } } as unknown as CurrentUserView;
const business = {
  id: "business_1",
  name: "Trattoria Da Gino",
  status: "live",
  viewer_role: "staff",
  timezone: "Europe/Rome",
  currency_code: "EUR",
} as unknown as BusinessView;
// 2 November 2026, 10:00 in Rome.
const GIVEN_AT = 1_793_610_000_000_000;

function detailWith(consent: Consent, erasedAt: number | null = null): CustomerDetail {
  return {
    contact: {
      id: "contact_a",
      name: "Giulia Rossi",
      is_phone_masked: false,
      is_phone_verified: true,
      erased_at: erasedAt,
      tags: [],
      is_vip: false,
      is_blocked: false,
    },
    visit_count: 1,
    standing: "visited",
    blocked_at: null,
    marketing_consent: consent,
  } as unknown as CustomerDetail;
}

function Harness({ initial }: { initial: CustomerDetail }) {
  const [data, setData] = useState<CustomerDetail | undefined>(initial);
  const query = {
    data,
    error: null,
    isLoading: false,
    isFetching: false,
    isPlaceholder: false,
    updatedAt: 0,
    reload: () => undefined,
    setData: (update: CustomerDetail | ((current: CustomerDetail | undefined) => CustomerDetail | undefined)) =>
      setData((current) => (typeof update === "function" ? update(current) : update)),
  } satisfies Query<CustomerDetail>;
  return <MarketingConsentCard detail={query} naming={{ name: "Giulia Rossi", isOwn: true }} />;
}

function renderCard(consent: Consent, locale: Locale = "en", erasedAt: number | null = null) {
  return renderInLocale(
    <BusinessProvider business={business} me={me}>
      <Harness initial={detailWith(consent, erasedAt)} />
    </BusinessProvider>,
    { locale },
  );
}

describe("MarketingConsentCard: whether marketing may reach the customer", () => {
  beforeEach(() => {
    vi.mocked(api.PATCH).mockReset();
  });

  it("says that nothing is sent without consent, and records one given in person after asking", async () => {
    const t = textsIn("en").t;
    vi.mocked(api.PATCH).mockReturnValue(
      ok({ contact_id: "contact_a", marketing_consent: { status: "agreed", given_at: GIVEN_AT, source: "in_person", text_version: "2026-11-02", recorded_by: "user_staff" } }) as never,
    );
    renderCard({ status: "not_given" });
    expect(screen.getByText(t("customers.consent.notGiven"))).toBeTruthy();

    await userEvent.click(screen.getByRole("button", { name: t("customers.consent.record") }));
    const dialog = await screen.findByRole("dialog");
    expect(dialog.textContent).toContain("Trattoria Da Gino");
    await userEvent.click(screen.getByRole("button", { name: t("customers.consent.confirm") }));

    expect(api.PATCH).toHaveBeenCalledWith("/v1/businesses/{business_id}/contacts/{contact_id}/card", {
      params: { path: { business_id: "business_1", contact_id: "contact_a" } },
      body: { marketing_consent: true },
    });
    await waitFor(() => expect(screen.getByText(t("customers.consent.sources.in_person"))).toBeTruthy());
    expect(screen.getByText(t("customers.consent.version", { version: "2026-11-02" }))).toBeTruthy();
  });

  it("shows an agreed consent in Italian and takes it back without asking", async () => {
    const t = textsIn("it").t;
    vi.mocked(api.PATCH).mockReturnValue(
      ok({ contact_id: "contact_a", marketing_consent: { status: "withdrawn", given_at: GIVEN_AT, withdrawn_at: GIVEN_AT, withdrawal: "in_person" } }) as never,
    );
    renderCard({ status: "agreed", given_at: GIVEN_AT, source: "booking_page", text_version: "2026-11-02" }, "it");
    expect(screen.getByText(t("customers.consent.sources.booking_page"))).toBeTruthy();

    await userEvent.click(screen.getByRole("button", { name: t("customers.consent.withdraw") }));

    expect(api.PATCH).toHaveBeenCalledWith(expect.any(String), expect.objectContaining({ body: { marketing_consent: false } }));
    await waitFor(() => expect(screen.getByText(t("customers.consent.withdrawals.in_person"))).toBeTruthy());
    expect(screen.getByRole("button", { name: t("customers.consent.record") })).toBeTruthy();
  });

  it("never says agreed while messages to the customer are stopped, and records nothing new then", () => {
    const t = textsIn("en").t;
    renderCard({ status: "stopped" });

    expect(screen.getByText(t("customers.consent.stopped"))).toBeTruthy();
    expect(screen.queryByText(/Agreed on/)).toBeNull();
    expect(screen.queryByRole("button")).toBeNull();
  });

  it("still takes back a consent recorded before messages were stopped", async () => {
    const t = textsIn("en").t;
    vi.mocked(api.PATCH).mockReturnValue(
      ok({ contact_id: "contact_a", marketing_consent: { status: "stopped", given_at: GIVEN_AT, withdrawn_at: GIVEN_AT, withdrawal: "in_person" } }) as never,
    );
    renderCard({ status: "stopped", given_at: GIVEN_AT, source: "booking_page", text_version: "2026-11-02" });
    expect(screen.queryByText(/Agreed on/)).toBeNull();
    expect(screen.queryByRole("button", { name: t("customers.consent.record") })).toBeNull();

    await userEvent.click(screen.getByRole("button", { name: t("customers.consent.withdraw") }));

    expect(api.PATCH).toHaveBeenCalledWith(expect.any(String), expect.objectContaining({ body: { marketing_consent: false } }));
    await waitFor(() => expect(screen.queryByRole("button", { name: t("customers.consent.withdraw") })).toBeNull());
    expect(screen.queryByRole("button", { name: t("customers.consent.record") })).toBeNull();
    expect(screen.getByText(t("customers.consent.stopped"))).toBeTruthy();
  });

  it("shows the team the very wording of the booking page's box", () => {
    for (const locale of ["en", "it"] as const) {
      expect(textsIn(locale).t("customers.consent.wording")).toBe(`${locale === "en" ? "“" : "«"}${marketingConsentTexts(locale).label}${locale === "en" ? "”" : "»"}`);
    }
  });

  it("is not shown for an erased customer", () => {
    renderCard({ status: "not_given" }, "en", GIVEN_AT);

    expect(screen.queryByTestId("marketing-consent-card")).toBeNull();
  });
});
