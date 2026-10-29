import { describe, expect, it } from "vitest";

import { isRoutePrefetch } from "./network";

describe("isRoutePrefetch", () => {
  it("knows Next.js's prefetches of other routes by their headers", () => {
    expect(isRoutePrefetch({ "next-router-prefetch": "1", rsc: "1" })).toBe(true);
    expect(isRoutePrefetch({ "next-router-segment-prefetch": "/_tree", rsc: "1" })).toBe(true);
  });

  it("counts a navigation's own data and every other request", () => {
    expect(isRoutePrefetch({ rsc: "1", "next-router-state-tree": "%5B%5D" })).toBe(false);
    expect(isRoutePrefetch({ accept: "application/json" })).toBe(false);
  });
});
