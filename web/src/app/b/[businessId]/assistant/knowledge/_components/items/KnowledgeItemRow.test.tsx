import { screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";

import type { BusinessView, CurrentUserView, KnowledgeItemDetails } from "@/api/types";
import { BusinessProvider } from "@/components/business/BusinessContext";
import { renderInLocale, textsIn } from "@/test/render";

import { KnowledgeItemRow } from "./KnowledgeItemRow";

const business = {
  id: "business_1",
  viewer_role: "owner",
  status: "live",
  currency_code: "EUR",
  timezone: "Europe/Rome",
} as unknown as BusinessView;
const me = { user: { id: "user_1", is_platform_admin: false } } as unknown as CurrentUserView;
const item = {
  id: "knowledge_1",
  business_id: "business_1",
  kind: "faq",
  title: "Regulars",
  body: "Giorgi, +39 333 123 4567",
  source: "owner",
  is_active: true,
  created_at: 1,
  updated_at: 1,
} as unknown as KnowledgeItemDetails;

function Owner({ children }: { children: ReactNode }) {
  return (
    <BusinessProvider business={business} me={me}>
      {children}
    </BusinessProvider>
  );
}

function renderRow(row: KnowledgeItemDetails, locale: "en" | "it") {
  return renderInLocale(
    <Owner>
      <ul>
        <KnowledgeItemRow item={row} resources={[]} onToggle={vi.fn()} onEdit={vi.fn()} onDelete={vi.fn()} />
      </ul>
    </Owner>,
    { locale },
  );
}

describe("KnowledgeItemRow: an item that names an erased customer (PRIV-08)", () => {
  it.each(["en", "it"] as const)("is flagged with what the owner should do (%s)", (locale) => {
    const { t } = textsIn(locale);
    renderRow({ ...item, erased_customer_flagged_at: 1_790_000_000_000_000 }, locale);

    expect(screen.getByText(t("knowledge.items.erasedCustomer"))).toBeTruthy();
    expect(screen.getByText(t("knowledge.items.erasedCustomerHint"))).toBeTruthy();
    // The owner's own text stays as written.
    expect(screen.getByText("Giorgi, +39 333 123 4567")).toBeTruthy();
  });

  it("shows no flag on other items", () => {
    const { t } = textsIn("en");
    renderRow(item, "en");

    expect(screen.queryByText(t("knowledge.items.erasedCustomer"))).toBeNull();
  });
});
