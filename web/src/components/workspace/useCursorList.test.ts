import { describe, expect, it } from "vitest";

import { visibleCursorItems } from "./useCursorList";

const ITEMS = ["first", "second"];

describe("visibleCursorItems", () => {
  it("shows the loaded items while nothing failed", () => {
    expect(visibleCursorItems(ITEMS, ["all", 0], ["blocked", 0], false)).toEqual(ITEMS);
  });

  it("keeps the items when a reload of the same filters failed", () => {
    // The key carries the reload counter last; the filters are the same.
    expect(visibleCursorItems(ITEMS, ["blocked", 0], ["blocked"], true)).toEqual(ITEMS);
  });

  it("hides the items when the first page for other filters failed", () => {
    // They belong to the earlier filters and would read as the filtered result.
    expect(visibleCursorItems(ITEMS, ["all", 0], ["blocked"], true)).toEqual([]);
  });

  it("has nothing to show before any page arrived", () => {
    expect(visibleCursorItems([], null, ["blocked"], true)).toEqual([]);
  });
});
