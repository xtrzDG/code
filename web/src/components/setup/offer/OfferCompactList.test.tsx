import { fireEvent, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { KnowledgeItemKind } from "@/api/types";
import type { Locale } from "@/i18n/config";
import type { TunnelOfferRow } from "@/lib/tunnel/offer";
import { renderInLocale, textsIn } from "@/test/render";

import { OfferTable } from "./OfferTable";
import type { OfferRows } from "./useOfferRows";

function row(key: string, title: string, kind: KnowledgeItemKind, price = "25", duration = "45"): TunnelOfferRow {
  return {
    key,
    id: `item_${key}`,
    kind,
    title,
    body: "",
    price,
    duration,
    kept: { tags: [], attributes: [], languages: [], is_active: true },
    baseline: "saved",
    isSuggestion: false,
  };
}

const SALON = [
  row("1", "Haircut", "service"),
  row("2", "Beard trim", "service", "15", "20"),
  row("3", "Colouring", "service", "", ""),
  row("4", "Manicure", "service"),
  row("5", "Pedicure", "service"),
  row("6", "Wedding look", "package", "300", ""),
  row("7", "Spa day", "package", "120", ""),
];

function fakeTable(rows: TunnelOfferRow[], status: OfferRows["status"] = {}): OfferRows {
  return {
    rows,
    isLoading: false,
    error: null,
    status,
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

function onPhone(isPhone: boolean) {
  vi.spyOn(window, "matchMedia").mockImplementation(
    (query: string) =>
      ({
        matches: isPhone && query.includes("max-width: 39.98rem"),
        media: query,
        addEventListener: () => undefined,
        removeEventListener: () => undefined,
      }) as unknown as MediaQueryList,
  );
}

function renderOffer(table: OfferRows, locale: Locale = "en") {
  return renderInLocale(<OfferTable table={table} currency="GEL" mode="edit" kinds={["service", "package"]} />, { locale });
}

const names = () => screen.queryAllByRole("textbox").filter((input) => input.hasAttribute("data-offer-name"));

describe("the offer on a phone, once it is long", () => {
  afterEach(() => vi.restoreAllMocks());

  it("folds into groups with their counts, and a group into one short row per line", async () => {
    const user = userEvent.setup();
    const { t, tp } = textsIn("en");
    onPhone(true);
    renderOffer(fakeTable(SALON));

    expect(names()).toHaveLength(0);
    const services = screen.getByRole("button", { name: tp("profileEdit.offer.compact.group", 5, { kind: t("knowledge.kindGroups.service") }) });
    expect(services.getAttribute("aria-expanded")).toBe("false");
    expect(screen.getByRole("button", { name: "Packages: 2 lines" }).getAttribute("aria-expanded")).toBe("false");

    await user.click(services);
    const list = screen.getByRole("list", { name: t("knowledge.kindGroups.service") });
    expect(within(list).getAllByRole("button").map((button) => button.textContent)).toEqual([
      "Haircut25 GEL · 45 min",
      "Beard trim15 GEL · 20 min",
      `Colouring${t("profileEdit.offer.compact.noPrice")}`,
      "Manicure25 GEL · 45 min",
      "Pedicure25 GEL · 45 min",
    ]);
  });

  it("opens one line for editing at a time, and Done saves and folds it again", async () => {
    const user = userEvent.setup();
    const table = fakeTable(SALON.filter((line) => line.kind === "service").concat(row("8", "Kids haircut", "service")));
    onPhone(true);
    renderOffer(table);

    await user.click(screen.getByRole("button", { name: /^Beard trim/ }));
    expect(names().map((input) => (input as HTMLInputElement).value)).toEqual(["Beard trim"]);
    await user.click(screen.getByRole("button", { name: /^Manicure/ }));
    expect(names().map((input) => (input as HTMLInputElement).value)).toEqual(["Manicure"]);

    // Enter in the open line opens the next one.
    fireEvent.keyDown(names()[0] as HTMLElement, { key: "Enter" });
    expect(names().map((input) => (input as HTMLInputElement).value)).toEqual(["Pedicure"]);

    await user.click(screen.getByRole("button", { name: textsIn("en").t("common.done") }));
    expect(table.save).toHaveBeenCalledWith("5");
    expect(names()).toHaveLength(0);
  });

  it("finds lines by name across groups, case and accents aside", async () => {
    const user = userEvent.setup();
    const { t } = textsIn("de");
    onPhone(true);
    renderOffer(fakeTable(SALON), "de");

    await user.type(screen.getByRole("searchbox", { name: t("profileEdit.offer.compact.search") }), "DAY");
    expect(screen.getAllByRole("button", { name: /^Spa day/ })).toHaveLength(1);
    expect(screen.queryByRole("button", { name: /^Haircut/ })).toBeNull();

    await user.clear(screen.getByRole("searchbox"));
    await user.type(screen.getByRole("searchbox"), "zzz");
    expect(screen.getByRole("status").textContent).toBe(t("profileEdit.offer.compact.noMatches", { query: "zzz" }));
  });

  it("keeps a new, unsaved or failed line open, its group unfolded", () => {
    onPhone(true);
    const fresh = { ...row("new-1", "", "package", "", ""), id: null };
    renderOffer(fakeTable([...SALON, fresh], { "3": "failed" }));
    expect(names().map((input) => (input as HTMLInputElement).value)).toEqual(["Colouring", ""]);
    expect(screen.getByRole("button", { name: "Services: 5 lines" }).getAttribute("aria-expanded")).toBe("true");
  });

  it("speaks Russian plural counts", () => {
    const { t, tp } = textsIn("ru");
    onPhone(true);
    renderOffer(fakeTable(SALON), "ru");
    expect(screen.getByRole("button", { name: tp("profileEdit.offer.compact.group", 5, { kind: t("knowledge.kindGroups.service") }) })).toBeTruthy();
    expect(tp("profileEdit.offer.compact.group", 5, { kind: "Услуги" })).toBe("Услуги: 5 строк");
  });

  it("stays the full table on a larger screen, and for a short offer on a phone", () => {
    onPhone(false);
    const { unmount } = renderOffer(fakeTable(SALON));
    expect(names()).toHaveLength(SALON.length);
    unmount();

    onPhone(true);
    renderOffer(fakeTable(SALON.slice(0, 5)));
    expect(names()).toHaveLength(5);
    expect(screen.queryByRole("searchbox")).toBeNull();
  });
});
