import { screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { TunnelOfferRow } from "@/lib/tunnel/offer";
import { renderInLocale, textsIn } from "@/test/render";

import { OfferTable } from "./OfferTable";
import type { OfferRows } from "./useOfferRows";

const suggested: TunnelOfferRow = {
  key: "s1",
  id: null,
  kind: "service",
  title: "Taglio",
  body: "",
  price: "",
  duration: "",
  kept: { tags: [], attributes: [], languages: [], is_active: true },
  baseline: "new",
  isSuggestion: true,
} as unknown as TunnelOfferRow;

function table(rows: TunnelOfferRow[]): OfferRows {
  return {
    rows,
    isLoading: false,
    error: null,
    status: {},
    showErrors: false,
    update: vi.fn(),
    add: vi.fn(),
    paste: vi.fn(() => 0),
    save: vi.fn(() => Promise.resolve(true)),
    remove: vi.fn(),
    saveAll: vi.fn(() => Promise.resolve(true)),
    reload: vi.fn(),
  } as unknown as OfferRows;
}

describe("suggested lines of the offer", () => {
  afterEach(() => vi.restoreAllMocks());

  it.each(["en", "it"] as const)("are marked as suggested, not as examples (%s)", (locale) => {
    const { t } = textsIn(locale);
    renderInLocale(<OfferTable table={table([suggested])} currency="EUR" mode="edit" kinds={["service"]} />, { locale });

    expect(screen.getByText(t("tunnelOffer.offer.suggestion"), { exact: true })).toBeTruthy();
    expect(t("tunnelOffer.offer.suggestion")).toBe(locale === "en" ? "Suggested" : "Suggerito");
    expect(document.body.textContent).not.toMatch(/Example|Esempio|esempi/);
  });
});
