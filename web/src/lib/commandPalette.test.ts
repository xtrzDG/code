import { describe, expect, it } from "vitest";

import {
  MAX_SEARCH_LENGTH,
  NAVIGATION_LIMIT,
  foldText,
  isPaletteShortcut,
  matchNavigation,
  movedIndex,
  navigationEntries,
  orderedEntries,
  searchTextOf,
  type PaletteEntry,
} from "./commandPalette";

const key = (key: string, modifiers: Partial<Record<"metaKey" | "ctrlKey" | "altKey", boolean>> = {}) => ({
  key,
  metaKey: false,
  ctrlKey: false,
  altKey: false,
  ...modifiers,
});

describe("the command palette", () => {
  it("opens on Cmd+K and Ctrl+K only, never on / or K alone", () => {
    expect(isPaletteShortcut(key("k", { metaKey: true }))).toBe(true);
    expect(isPaletteShortcut(key("K", { ctrlKey: true }))).toBe(true);
    expect(isPaletteShortcut(key("k"))).toBe(false);
    expect(isPaletteShortcut(key("/"))).toBe(false);
    expect(isPaletteShortcut(key("/", { ctrlKey: true }))).toBe(false);
    expect(isPaletteShortcut(key("k", { ctrlKey: true, altKey: true }))).toBe(false);
  });

  it("lists every page once, with its section beside it", () => {
    const entries = navigationEntries([
      { href: "/b/x/overview", label: "Overview", pages: [{ href: "/b/x/overview", label: "Dashboard" }] },
      {
        href: "/b/x/customers",
        label: "Customers",
        pages: [
          { href: "/b/x/customers", label: "All customers" },
          { href: "/b/x/customers/segments", label: "Segments" },
        ],
      },
      { href: "/b/x/overview", label: "Overview again" },
    ]);

    expect(entries.map((entry) => [entry.label, entry.detail, entry.href])).toEqual([
      ["Overview", undefined, "/b/x/overview"],
      ["All customers", "Customers", "/b/x/customers"],
      ["Segments", "Customers", "/b/x/customers/segments"],
    ]);
    expect(entries.every((entry) => entry.group === "navigation")).toBe(true);
  });

  it("matches every typed word in a page or its section, without case or accents", () => {
    const entries = navigationEntries([
      { href: "/s", label: "Settings", pages: [{ href: "/s/team", label: "Team" }, { href: "/s/privacy", label: "Privacy" }] },
      { href: "/c", label: "Клиенты", pages: [{ href: "/c", label: "Все клиенты" }, { href: "/c/s", label: "Сегменты" }] },
    ]);

    expect(matchNavigation(entries, "set TEAM").map((entry) => entry.href)).toEqual(["/s/team"]);
    expect(matchNavigation(entries, "клиент").map((entry) => entry.href)).toEqual(["/c", "/c/s"]);
    expect(matchNavigation(entries, "nothing")).toEqual([]);
    expect(foldText("Café ÉTÉ")).toBe("cafe ete");
  });

  it("shows at most a few pages", () => {
    const many = navigationEntries(Array.from({ length: 20 }, (_, index) => ({ href: `/p${index}`, label: `Page ${index}` })));

    expect(matchNavigation(many, "")).toHaveLength(NAVIGATION_LIMIT);
  });

  it("searches from two characters, trimmed and cut to the API's limit", () => {
    expect(searchTextOf(" n ")).toBeNull();
    expect(searchTextOf("  ni ")).toBe("ni");
    expect(searchTextOf("x".repeat(150))).toHaveLength(MAX_SEARCH_LENGTH);
  });

  it("moves the highlight with the arrows, Home and End, and wraps", () => {
    expect(movedIndex(-1, 3, "ArrowDown")).toBe(0);
    expect(movedIndex(2, 3, "ArrowDown")).toBe(0);
    expect(movedIndex(0, 3, "ArrowUp")).toBe(2);
    expect(movedIndex(-1, 3, "ArrowUp")).toBe(2);
    expect(movedIndex(1, 3, "Home")).toBe(0);
    expect(movedIndex(1, 3, "End")).toBe(2);
    expect(movedIndex(1, 3, "Tab")).toBe(1);
    expect(movedIndex(0, 0, "ArrowDown")).toBe(-1);
  });

  it("orders the groups: pages, customers, conversations, bookings", () => {
    const entry = (id: string, group: PaletteEntry["group"]): PaletteEntry => ({ id, group, label: id, href: `/${id}` });

    expect(
      orderedEntries({
        bookings: [entry("b", "bookings")],
        customers: [entry("c", "customers")],
        navigation: [entry("n", "navigation")],
      }).map((item) => item.id),
    ).toEqual(["n", "c", "b"]);
  });
});
