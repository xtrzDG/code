import { describe, expect, it } from "vitest";

import { freshness } from "./freshness";

const NOW = 1_790_812_800_000;

describe("freshness", () => {
  it("says just now, minutes, then the time", () => {
    expect(freshness(0, NOW)).toEqual({ kind: "never" });
    expect(freshness(NOW - 59_000, NOW)).toEqual({ kind: "justNow" });
    expect(freshness(NOW + 5_000, NOW)).toEqual({ kind: "justNow" });
    expect(freshness(NOW - 61_000, NOW)).toEqual({ kind: "minutes", minutes: 1 });
    expect(freshness(NOW - 59 * 60_000, NOW)).toEqual({ kind: "minutes", minutes: 59 });
    expect(freshness(NOW - 2 * 60 * 60_000, NOW)).toEqual({ kind: "at", at: new Date(NOW - 2 * 60 * 60_000) });
  });
});
