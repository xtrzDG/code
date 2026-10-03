import { describe, expect, it } from "vitest";

import { appendPage, fromFirstPage, MAX_PAGE_SIZE, PAGE_SIZE, reloadLimit, withNextPage } from "./paging";

describe("server paging", () => {
  it("reloads as many items as are shown, within one API page", () => {
    expect(reloadLimit(0)).toBe(PAGE_SIZE);
    expect(reloadLimit(50)).toBe(50);
    expect(reloadLimit(51)).toBe(100);
    expect(reloadLimit(1000)).toBe(MAX_PAGE_SIZE);
    expect(reloadLimit(30, 25)).toBe(50);
  });

  it("appends a page without repeating items that moved", () => {
    const shown = [{ id: "a" }, { id: "b" }];
    expect(appendPage(shown, [{ id: "b" }, { id: "c" }]).map((item) => item.id)).toEqual(["a", "b", "c"]);
    expect(appendPage([], [{ id: "x" }])).toEqual([{ id: "x" }]);
  });

  it("can tell items apart by another field", () => {
    const shown = [{ business_id: "a" }];
    const next = [{ business_id: "a" }, { business_id: "b" }];
    expect(appendPage(shown, next, (item) => item.business_id)).toEqual([{ business_id: "a" }, { business_id: "b" }]);
  });

  it("caches a first page with its totals and cursor", () => {
    const page = { items: [{ id: "a" }], next_cursor: "a", open_count: 3 };
    expect(fromFirstPage(page)).toEqual({ page, items: [{ id: "a" }], nextCursor: "a" });
    expect(fromFirstPage({ items: [] })).toEqual({ page: { items: [] }, items: [], nextCursor: null });
  });

  it("adds a next page only to the list it continues", () => {
    const data = fromFirstPage({ items: [{ id: "a" }], next_cursor: "a" });
    expect(withNextPage(data, "a", { items: [{ id: "b" }], next_cursor: null })).toEqual({
      page: data.page,
      items: [{ id: "a" }, { id: "b" }],
      nextCursor: null,
    });
    // The list was reloaded meanwhile: the page belongs to the old one.
    expect(withNextPage(data, "z", { items: [{ id: "b" }] })).toBe(data);
    expect(withNextPage(undefined, "a", { items: [{ id: "b" }] })).toBeUndefined();
  });
});
