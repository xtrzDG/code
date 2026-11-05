import { describe, expect, it } from "vitest";

import { autoScrollStep, EDGE_ZONE_PX, edgeStep, MAX_STEP_PX, visibleBox } from "./edgeScroll";

const grid = { left: 100, top: 200, right: 900, bottom: 700 };

describe("scrolling the grid while a booking is dragged near its edge", () => {
  it("leaves the middle alone", () => {
    expect(autoScrollStep({ x: 500, y: 450 }, grid)).toEqual({ dx: 0, dy: 0 });
  });

  it("scrolls toward the edge the pointer is near, faster the closer it is", () => {
    const nearBottom = edgeStep(grid.bottom - EDGE_ZONE_PX / 2, grid.top, grid.bottom);
    const atBottom = edgeStep(grid.bottom - 1, grid.top, grid.bottom);
    expect(nearBottom).toBeGreaterThan(0);
    expect(atBottom).toBeGreaterThan(nearBottom);
    expect(edgeStep(grid.top + 1, grid.top, grid.bottom)).toBeLessThan(0);
    expect(edgeStep(grid.right - 1, grid.left, grid.right)).toBeGreaterThan(0);
    expect(edgeStep(grid.left + 1, grid.left, grid.right)).toBeLessThan(0);
  });

  it("starts gently at the zone's inner border and never stalls inside it", () => {
    expect(edgeStep(grid.bottom - EDGE_ZONE_PX + 1, grid.top, grid.bottom)).toBe(1);
    expect(edgeStep(grid.bottom - EDGE_ZONE_PX, grid.top, grid.bottom)).toBe(0);
  });

  it("goes at full speed past the edge, on both axes at once in a corner", () => {
    expect(autoScrollStep({ x: grid.right + 300, y: grid.top - 300 }, grid)).toEqual({ dx: MAX_STEP_PX, dy: -MAX_STEP_PX });
    expect(autoScrollStep({ x: grid.left - 1, y: grid.bottom + 1 }, grid)).toEqual({ dx: -MAX_STEP_PX, dy: MAX_STEP_PX });
  });

  it("keeps a still middle in a small grid and does nothing in an empty one", () => {
    expect(edgeStep(130, 100, 160)).toBe(0);
    expect(edgeStep(101, 100, 160)).toBeLessThan(0);
    expect(edgeStep(5, 10, 10)).toBe(0);
  });

  it("measures the edges of what is on screen", () => {
    expect(visibleBox({ left: -50, top: 300, right: 1200, bottom: 1400 }, { width: 1000, height: 800 })).toEqual({
      left: 0,
      top: 300,
      right: 1000,
      bottom: 800,
    });
  });
});
