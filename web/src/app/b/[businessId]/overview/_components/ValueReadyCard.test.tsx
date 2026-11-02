import { screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { BusinessView, CurrentUserView } from "@/api/types";
import { BusinessProvider } from "@/components/business/BusinessContext";
import type { ValueModel } from "@/components/value/valueModel";
import { answerGet, ok } from "@/test/fakeApi";
import { renderInLocale, textsIn } from "@/test/render";

import { ValueReadyCard } from "./ValueReadyCard";

vi.mock("@/api/client", () => ({ api: { GET: vi.fn(), POST: vi.fn(), PATCH: vi.fn(), DELETE: vi.fn() } }));
vi.mock("@/components/setup/QrImage", () => ({ QrImage: ({ label }: { label: string }) => <img alt={label} /> }));

const business = { id: "business_1", viewer_role: "owner", status: "live", currency_code: "EUR", timezone: "Europe/Rome" } as unknown as BusinessView;
const me = { user: { id: "user_owner", is_platform_admin: false } } as unknown as CurrentUserView;

const model = {
  business_id: "business_1",
  currency_code: "EUR",
  date_from: "2026-11-01",
  date_to: "2026-11-02",
  is_since_launch: true,
  is_trial: false,
  average_check_minor: 2500,
  current: { conversation_count: 0 },
} as unknown as ValueModel;

describe("ValueReadyCard", () => {
  it.each(["en", "it"] as const)("says what will appear without made-up numbers (%s)", async (locale) => {
    answerGet(() => ok({ hosted_chat_url: "https://app.example.com/c/trattoria-da-marco" }));
    const { container } = renderInLocale(
      <BusinessProvider business={business} me={me}>
        <ValueReadyCard model={model} isPlaceholder={false} />
      </BusinessProvider>,
      { locale },
    );
    const { t } = textsIn(locale);

    expect(screen.getByText(t("value.ready.lead"))).toBeTruthy();
    expect(screen.getByText(t("value.ready.body"))).toBeTruthy();
    expect(await screen.findByText("app.example.com/c/trattoria-da-marco")).toBeTruthy();
    expect(container.querySelector("[data-value-sample]")).toBeNull();
    expect(container.textContent).not.toMatch(/\b12\b|€/);
  });
});
