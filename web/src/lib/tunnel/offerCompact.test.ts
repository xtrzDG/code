import { describe, expect, it } from "vitest";

import { groupByKind, matchesQuery, rowMinutes } from "./offerCompact";

describe("the folded offer on a phone", () => {
  it("groups the lines by kind, the niche's kinds first, keeping the lines' order", () => {
    const rows = [
      { key: "a", kind: "package" as const },
      { key: "b", kind: "service" as const },
      { key: "c", kind: "product" as const },
      { key: "d", kind: "service" as const },
    ];
    expect(groupByKind(rows, ["service", "package", "room_type"]).map((group) => [group.kind, group.rows.map((row) => row.key)])).toEqual([
      ["service", ["b", "d"]],
      ["package", ["a"]],
      ["product", ["c"]],
    ]);
    expect(groupByKind([], ["service"])).toEqual([]);
  });

  it("finds a line by any part of its name, case and accents aside", () => {
    expect(matchesQuery("Café latte", "cafe", "en")).toBe(true);
    expect(matchesQuery("Елка новогодняя", "ёлка", "ru")).toBe(true);
    expect(matchesQuery("Haircut", "  CUT ", "en")).toBe(true);
    expect(matchesQuery("Haircut", "beard", "en")).toBe(false);
    expect(matchesQuery("ხაჭაპური", "ხაჭა", "ka")).toBe(true);
    expect(matchesQuery("anything", "   ", "de")).toBe(true);
  });

  it("shows the minutes only of a kind that lasts and only a whole number of them", () => {
    expect(rowMinutes({ kind: "service", duration: "45" })).toBe(45);
    expect(rowMinutes({ kind: "service", duration: "" })).toBeNull();
    expect(rowMinutes({ kind: "service", duration: "4.5" })).toBeNull();
    expect(rowMinutes({ kind: "menu_item", duration: "45" })).toBeNull();
  });
});
