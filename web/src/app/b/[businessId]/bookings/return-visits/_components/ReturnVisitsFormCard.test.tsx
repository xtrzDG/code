import { screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { CurrentUserView } from "@/api/types";
import { business } from "@/app/b/[businessId]/settings/_lib/settingsFixtures";
import { BusinessProvider } from "@/components/business/BusinessContext";
import { renderInLocale, textsIn } from "@/test/render";

import type { CampaignSettingsView } from "../_lib/returnVisitsModel";
import type { ReturnVisitsState } from "../_lib/useReturnVisits";
import { ReturnVisitsFormCard } from "./ReturnVisitsFormCard";

vi.mock("@/api/client", () => ({ api: { GET: vi.fn(), POST: vi.fn(), PUT: vi.fn(), DELETE: vi.fn() } }));

const me = { user: { id: "user_owner", is_platform_admin: false } } as unknown as CurrentUserView;

const stored: CampaignSettingsView = {
  audience: "all_customers",
  delay_days: 30,
  is_enabled: true,
  month_sent_count: 3,
  monthly_cap: 100,
  niche_delay_days: 30,
  niche_rule_kind: "rebook",
  rule_kind: "rebook",
};

const state = {
  save: { run: vi.fn(), isPending: false, error: null },
  settings: { setData: vi.fn() },
  segments: { data: { items: [], next_cursor: null } },
} as unknown as ReturnVisitsState;

describe("ReturnVisitsFormCard: who the invitations go to", () => {
  it.each(["en", "it"] as const)("says only customers who agreed get them, in the chat they booked in (%s)", (locale) => {
    renderInLocale(
      <BusinessProvider business={business} me={me}>
        <ReturnVisitsFormCard stored={stored} state={state} />
      </BusinessProvider>,
      { locale },
    );
    const { t } = textsIn(locale);

    expect(screen.getByText(t("returnVisits.settings.consent"))).toBeTruthy();
  });

  it("words the rule plainly in both languages", () => {
    expect(textsIn("en").t("returnVisits.settings.consent")).toMatch(/only to customers who agreed to marketing messages/);
    expect(textsIn("en").t("returnVisits.settings.consent")).toMatch(/only in the chat where they made the booking/);
    expect(textsIn("it").t("returnVisits.settings.consent")).toMatch(/solo ai clienti che hanno accettato i messaggi promozionali/);
    expect(textsIn("it").t("returnVisits.settings.consent")).toMatch(/solo nella chat in cui hanno fatto la prenotazione/);
  });
});
