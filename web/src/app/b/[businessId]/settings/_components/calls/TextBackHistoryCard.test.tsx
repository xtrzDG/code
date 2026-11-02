import { screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it } from "vitest";

import type { BusinessView, CurrentUserView } from "@/api/types";
import type { Query } from "@/api/useQuery";
import { BusinessProvider } from "@/components/business/BusinessContext";
import { renderInLocale, textsIn } from "@/test/render";

import type { TextBackPage, TextBackView } from "../../_lib/calls";
import { TextBackHistoryCard } from "./TextBackHistoryCard";

const RAW = "Twilio 21610: the number is unsubscribed (SMS_FROM_NUMBER).";
const business = {
  id: "business_1",
  viewer_role: "owner",
  status: "live",
  currency_code: "EUR",
  timezone: "Europe/Rome",
} as unknown as BusinessView;
const failed = {
  id: "missed_call_00000000-0000-5000-8000-000000000001",
  reason: "busy",
  source: "pbx",
  caller_phone_number: "+393331234567",
  called_at: 1_790_000_000_000_000,
  language: "it",
  status: "failed",
  channel: "sms",
  last_error: RAW,
} as unknown as TextBackView;

function page(items: TextBackView[]): Query<TextBackPage> {
  return { data: { items, next_cursor: null }, error: null, reload: () => undefined } as unknown as Query<TextBackPage>;
}

function asViewer(isPlatformAdmin: boolean) {
  const me = { user: { id: "user_1", is_platform_admin: isPlatformAdmin } } as unknown as CurrentUserView;
  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <BusinessProvider business={business} me={me}>
        {children}
      </BusinessProvider>
    );
  };
}

describe("TextBackHistoryCard", () => {
  it.each(["en", "it"] as const)("tells the owner a text-back failed without the raw error (%s)", (locale) => {
    const Owner = asViewer(false);
    renderInLocale(
      <Owner>
        <TextBackHistoryCard textBacks={page([failed])} />
      </Owner>,
      { locale },
    );

    expect(screen.getByText(textsIn(locale).t("common.deliveryProblem"))).toBeTruthy();
    expect(document.body.textContent).not.toContain("Twilio");
  });

  it("shows the raw error to platform admins", () => {
    const Admin = asViewer(true);
    renderInLocale(
      <Admin>
        <TextBackHistoryCard textBacks={page([failed])} />
      </Admin>,
    );

    expect(screen.getByText(RAW)).toBeTruthy();
  });
});
