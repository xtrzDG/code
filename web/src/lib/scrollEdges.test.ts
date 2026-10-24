import { describe, expect, it } from "vitest";

import { scrollEdges } from "./scrollEdges";

describe("scroll edges", () => {
  it("show nothing when everything fits", () => {
    expect(scrollEdges(0, 300, 300, false)).toEqual({ left: false, right: false });
    expect(scrollEdges(0, 300.5, 300, false)).toEqual({ left: false, right: false });
  });

  it("fade the end of a row at its start, both sides in the middle, the start at its end", () => {
    expect(scrollEdges(0, 600, 300, false)).toEqual({ left: false, right: true });
    expect(scrollEdges(150, 600, 300, false)).toEqual({ left: true, right: true });
    expect(scrollEdges(300, 600, 300, false)).toEqual({ left: true, right: false });
  });

  it("mirror a right-to-left row (negative scrollLeft)", () => {
    expect(scrollEdges(0, 600, 300, true)).toEqual({ left: true, right: false });
    expect(scrollEdges(-150, 600, 300, true)).toEqual({ left: true, right: true });
    expect(scrollEdges(-300, 600, 300, true)).toEqual({ left: false, right: true });
  });
});
