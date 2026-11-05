import { describe, expect, it } from "vitest";

import { INBOX_VIEWS } from "@/lib/navigation";

import { MORE_INBOX_VIEWS, PRIMARY_INBOX_VIEWS, isMoreInboxView, menuTarget } from "./viewTabs";

describe("inbox view tabs", () => {
  it("keep the three working views in the row and the rest under More", () => {
    expect(PRIMARY_INBOX_VIEWS).toEqual(["needs_person", "requests", "mine"]);
    expect(MORE_INBOX_VIEWS).toEqual(["unassigned", "all"]);
    expect([...PRIMARY_INBOX_VIEWS, ...MORE_INBOX_VIEWS].sort()).toEqual([...INBOX_VIEWS].sort());
  });

  it("tell which views live under More", () => {
    expect(isMoreInboxView("all")).toBe(true);
    expect(isMoreInboxView("unassigned")).toBe(true);
    expect(isMoreInboxView("mine")).toBe(false);
  });

  it("move through the More menu with arrows, Home and End", () => {
    expect(menuTarget("ArrowDown", 0, 2)).toBe(1);
    expect(menuTarget("ArrowDown", 1, 2)).toBe(0);
    expect(menuTarget("ArrowUp", 0, 2)).toBe(1);
    expect(menuTarget("ArrowUp", -1, 2)).toBe(0);
    expect(menuTarget("Home", 1, 2)).toBe(0);
    expect(menuTarget("End", 0, 2)).toBe(1);
    expect(menuTarget("Enter", 0, 2)).toBeNull();
    expect(menuTarget("ArrowDown", 0, 0)).toBeNull();
  });
});
