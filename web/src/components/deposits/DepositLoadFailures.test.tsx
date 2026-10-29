import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "@/api/client";
import { queryCache } from "@/api/queryCache";
import type { CurrentUserView } from "@/api/types";
import { BusinessProvider } from "@/components/business/BusinessContext";
import type { Locale } from "@/i18n/config";
import { answerGet, failure, ok, pending } from "@/test/fakeApi";
import { renderInLocale, textsIn } from "@/test/render";

import { business } from "../../app/b/[businessId]/settings/_lib/settingsFixtures";
import { DepositPayment } from "./DepositPayment";
import { DepositPolicyPanel } from "./DepositPolicyPanel";
import type { BookingDepositView, DepositSettingsView } from "./depositModel";

vi.mock("@/api/client", () => ({ api: { GET: vi.fn(), POST: vi.fn(), PUT: vi.fn(), DELETE: vi.fn() } }));

const SETTINGS = "/v1/businesses/{business_id}/deposit-settings";
const DEPOSIT = "/v1/businesses/{business_id}/deposits/{deposit_id}";
const me = { user: { id: "user_owner", is_platform_admin: false } } as unknown as CurrentUserView;
const SERVER_ERROR = { error: { code: "internal", message: "Something went wrong." } };

const settings: DepositSettingsView = {
  currency_code: "GEL",
  currency_digits: 2,
  is_enabled: true,
  hold_minutes: 60,
  refund_cutoff_hours: 24,
  default_payment_link_id: null,
  payment_links: [],
  policies: [],
};
const deposit: BookingDepositView = {
  request_id: "deposit_request_1",
  status: "awaiting",
  amount_minor: 12000,
  currency_code: "GEL",
  hold_expires_at: 1_790_000_000_000_000,
};

function withBusiness(ui: React.ReactElement, locale: Locale = "en") {
  return renderInLocale(
    <BusinessProvider business={business} me={me}>
      {ui}
    </BusinessProvider>,
    { locale },
  );
}

describe("deposit panels when their data does not load", () => {
  beforeEach(() => {
    queryCache.clear();
    vi.mocked(api.GET).mockReset();
  });

  it.each(["en", "it"] as const)(
    "the policy panel offers a retry instead of a skeleton forever (%s)",
    async (locale) => {
      const { t } = textsIn(locale);
      let attempts = 0;
      answerGet((path) => {
        if (path !== SETTINGS) return pending();
        attempts += 1;
        return attempts === 1 ? failure(500, SERVER_ERROR) : ok(settings);
      });
      withBusiness(<DepositPolicyPanel target={{ target: "banquet" }} />, locale);

      const retry = await screen.findByRole("button", { name: t("common.retry") });
      await userEvent.setup().click(retry);

      expect(await screen.findByText(t("deposits.policy.noPage"))).toBeTruthy();
      expect(attempts).toBe(2);
    },
  );

  it("a deposit says its reference did not load and loads it again", async () => {
    const { t } = textsIn("en");
    let attempts = 0;
    answerGet((path) => {
      if (path !== DEPOSIT) return pending();
      attempts += 1;
      return attempts === 1
        ? failure(500, SERVER_ERROR)
        : ok({ id: deposit.request_id, reference: "DK7Q3M9X", payment_link_label: "Bank", status: "awaiting" });
    });
    withBusiness(
      <DepositPayment
        deposit={deposit}
        heldUntilKey="deposits.booking.heldUntil"
        confirmKey="deposits.booking.confirmDescription"
        onPaid={() => undefined}
      />,
    );

    expect(await screen.findByText(t("deposits.booking.referenceFailed"))).toBeTruthy();
    await userEvent.setup().click(screen.getByRole("button", { name: t("common.retry") }));

    expect(await screen.findByText(/DK7Q3M9X/)).toBeTruthy();
    expect(screen.queryByText(t("deposits.booking.referenceFailed"))).toBeNull();
  });
});
