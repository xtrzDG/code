import { screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { BusinessView, CurrentUserView, KnowledgeItemDetails } from "@/api/types";
import { BusinessProvider } from "@/components/business/BusinessContext";
import { renderInLocale, textsIn } from "@/test/render";

import { KnowledgeItemRow } from "./KnowledgeItemRow";

const business = { id: "business_1", viewer_role: "owner", currency_code: "EUR", timezone: "Europe/Rome" } as unknown as BusinessView;
const me = { user: { id: "user_1", is_platform_admin: false } } as unknown as CurrentUserView;
const item = { id: "knowledge_1", kind: "faq", title: "Regulars", body: "Giorgi, +39 333 123 4567", is_active: true } as unknown as KnowledgeItemDetails;

function renderRow(row: KnowledgeItemDetails, locale: "en" | "it") {
  return renderInLocale(
    <BusinessProvider business={business} me={me}>
      <ul>
        <KnowledgeItemRow item={row} resources={[]} onToggle={vi.fn()} onEdit={vi.fn()} onDelete={vi.fn()} />
      </ul>
    </BusinessProvider>,
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
