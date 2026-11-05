import { describe, expect, it } from "vitest";

import { splitForMiddleEllipsis } from "./middleEllipsis";

describe("splitForMiddleEllipsis", () => {
  it("keeps the last path segment as the tail", () => {
    expect(splitForMiddleEllipsis("localhost:3401/c/kofeynya-zerno")).toEqual({ head: "localhost:3401/c", tail: "/kofeynya-zerno" });
    expect(splitForMiddleEllipsis("app.example.com/c/mtsvane-ezo")).toEqual({ head: "app.example.com/c", tail: "/mtsvane-ezo" });
  });

  it("leaves text without a path (or ending in a slash) whole", () => {
    expect(splitForMiddleEllipsis("example.com")).toEqual({ head: "example.com", tail: "" });
    expect(splitForMiddleEllipsis("example.com/")).toEqual({ head: "example.com/", tail: "" });
    expect(splitForMiddleEllipsis("/c")).toEqual({ head: "/c", tail: "" });
  });
});
