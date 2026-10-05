import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { queryCache } from "@/api/queryCache";
import type { KnowledgeItemDetails, Schema } from "@/api/types";
import type { Locale } from "@/i18n/config";
import { rememberDoneExample } from "@/lib/tunnel/offerMemory";
import { answerGet, lastGetQuery, ok, pending } from "@/test/fakeApi";
import { Providers } from "@/test/render";

import { useOfferRows } from "./useOfferRows";

vi.mock("@/api/client", () => ({ api: { GET: vi.fn(), POST: vi.fn(), PATCH: vi.fn(), DELETE: vi.fn() } }));

const KNOWLEDGE = "/v1/businesses/{business_id}/knowledge";

type Example = Schema<"StarterOfferView">;

/** The niche's examples as the API names them in each interface language (same keys). */
const EXAMPLES: Record<Locale, Example[]> = {
  en: [
    { key: "business_lunch", kind: "menu_item", title: "Business lunch", duration_minutes: null },
    { key: "khachapuri", kind: "menu_item", title: "Khachapuri", duration_minutes: null },
  ],
  ru: [
    { key: "business_lunch", kind: "menu_item", title: "Бизнес-ланч", duration_minutes: null },
    { key: "khachapuri", kind: "menu_item", title: "Хачапури", duration_minutes: null },
  ],
  ka: [
    { key: "business_lunch", kind: "menu_item", title: "ბიზნეს-ლანჩი", duration_minutes: null },
    { key: "khachapuri", kind: "menu_item", title: "ხაჭაპური", duration_minutes: null },
  ],
};

function item(overrides: Partial<KnowledgeItemDetails>): KnowledgeItemDetails {
  return {
    id: "knowledge_1",
    business_id: "business_1",
    kind: "menu_item",
    title: "Бизнес-ланч",
    price_minor: 1800,
    currency_code: "GEL",
    duration_minutes: null,
    is_active: true,
    tags: [],
    attributes: [],
    languages: [],
    created_at: 1,
    updated_at: 1,
    ...overrides,
  } as KnowledgeItemDetails;
}

function rowsIn(locale: Locale, businessId: string, saved: KnowledgeItemDetails[]) {
  answerGet((path) => (path === KNOWLEDGE ? ok({ items: saved, next_cursor: null }) : pending()));
  const wrapper = ({ children }: { children: ReactNode }) => <Providers locale={locale}>{children}</Providers>;
  return renderHook(() => useOfferRows(businessId, EXAMPLES[locale], "GEL", "menu_item"), { wrapper });
}

async function shownRows(locale: Locale, businessId: string, saved: KnowledgeItemDetails[]) {
  const { result } = rowsIn(locale, businessId, saved);
  await waitFor(() => expect(result.current.isLoading).toBe(false));
  return result.current.rows.map((row) => [row.title, row.isSuggestion]);
}

describe("useOfferRows: the offer table never brings examples back across languages", () => {
  beforeEach(() => {
    queryCache.clear();
    window.localStorage.clear();
  });

  it("offers the niche's examples, in the interface language, to an empty table", async () => {
    expect(await shownRows("ka", "business_empty", [])).toEqual([
      ["ბიზნეს-ლანჩი", true],
      ["ხაჭაპური", true],
    ]);
  });

  it.each(["en", "ka", "ru"] as const)("shows only the line saved in Russian when reopened in %s", async (locale) => {
    expect(await shownRows(locale, `business_saved_${locale}`, [item({ title: "Бизнес-ланч" })])).toEqual([["Бизнес-ланч", false]]);
  });

  it("does not bring back, in Georgian, an example removed in a Russian session", async () => {
    rememberDoneExample(window.localStorage, "business_removed", "business_lunch");

    expect(await shownRows("ka", "business_removed", [])).toEqual([["ხაჭაპური", true]]);
  });

  it("asks for the items in the interface language", async () => {
    const { result } = rowsIn("ka", "business_language", []);
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(lastGetQuery().language).toBe("ka");
  });
});
