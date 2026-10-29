import { screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { queryCache } from "@/api/queryCache";
import type { CurrentUserView } from "@/api/types";
import { BusinessProvider } from "@/components/business/BusinessContext";
import type { DepositReport, NoShowRateView } from "@/components/deposits/depositModel";
import { answerGet, ok, pending } from "@/test/fakeApi";
import { renderInLocale, textsIn } from "@/test/render";

import { business } from "../../../settings/_lib/settingsFixtures";
import { DepositsCard } from "./DepositsCard";

vi.mock("@/api/client", () => ({ api: { GET: vi.fn(), POST: vi.fn(), PUT: vi.fn(), DELETE: vi.fn() } }));

const REPORT = "/v1/businesses/{business_id}/deposit-report";
const me = { user: { id: "user_owner", is_platform_admin: false } } as unknown as CurrentUserView;

function rate(finished: number, noShows: number): NoShowRateView {
  const isEnough = finished >= 20;
  return {
    finished_count: finished,
    no_show_count: noShows,
    has_enough_data: isEnough,
    no_show_percent: isEnough ? Math.round((noShows * 100) / finished) : null,
  };
}

function report(overrides: Partial<DepositReport> = {}): DepositReport {
  return {
    is_enabled: true,
    days: 30,
    starts_at: 1,
    ends_at: 2,
    requested_count: 4,
    paid_count: 3,
    expired_count: 1,
    awaiting_count: 0,
    money: [],
    with_deposit: rate(5, 0),
    without_deposit: rate(5, 1),
    min_sample: 20,
    ...overrides,
  };
}

function renderCard(view: DepositReport, locale: "en" | "it" = "en") {
  answerGet((path) => (path === REPORT ? ok(view) : pending()));
  return renderInLocale(
    <BusinessProvider business={business} me={me}>
      <DepositsCard />
    </BusinessProvider>,
    { locale },
  );
}

describe("DepositsCard: no-shows before deposits and since", () => {
  beforeEach(() => {
    queryCache.clear();
  });

  it.each(["en", "it"] as const)("compares the two periods once deposits went on (%s)", async (locale) => {
    const { t } = textsIn(locale);
    renderCard(
      report({ enabled_at: 1_790_000_000_000_000, before_deposits: rate(20, 5), since_deposits: rate(19, 1) }),
      locale,
    );

    expect(await screen.findByText(t("deposits.report.noShowBefore"))).toBeTruthy();
    expect(screen.getByText(t("deposits.report.noShowSince"))).toBeTruthy();
    // Since deposits there are too few finished visits to trust a share.
    expect(screen.getByText(t("deposits.report.notEnoughData", { finished: "19", min: "20" }))).toBeTruthy();
  });

  it("says nothing of before and after while deposits were never on", async () => {
    const { t } = textsIn("en");
    renderCard(report({ enabled_at: null, before_deposits: null, since_deposits: null }));

    expect(await screen.findByText(t("deposits.report.noShowWith"))).toBeTruthy();
    expect(screen.queryByText(t("deposits.report.noShowBefore"))).toBeNull();
  });
});
