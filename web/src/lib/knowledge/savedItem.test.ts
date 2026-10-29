import { describe, expect, it } from "vitest";

import { withSavedItem } from "./kinds";

const item = (id: string, kind: "faq" | "service", isActive = true) => ({ id, kind, is_active: isActive });

describe("withSavedItem", () => {
  const list = [item("a", "faq"), item("b", "service")];

  it("replaces a saved item in place", () => {
    const saved = { ...item("b", "service"), is_active: false };
    expect(withSavedItem(list, saved, { kind: "all", status: "all" })).toEqual([item("a", "faq"), saved]);
  });

  it("drops an item that no longer matches the filter (switched off in the active list)", () => {
    const saved = item("a", "faq", false);
    expect(withSavedItem(list, saved, { kind: "all", status: "active" }).map((entry) => entry.id)).toEqual(["b"]);
  });

  it("puts a new matching item first and leaves out one that does not match", () => {
    expect(withSavedItem(list, item("c", "faq"), { kind: "faq", status: "all" }).map((entry) => entry.id)).toEqual(["c", "a", "b"]);
    expect(withSavedItem(list, item("c", "faq"), { kind: "service", status: "all" })).toEqual(list);
  });
});
