/**
 * Scrolling the calendar while a booking is dragged near its edge: the
 * closer the pointer comes to an edge of the grid's visible part (or goes
 * past it), the faster the grid scrolls that way, on both axes. When the
 * grid cannot scroll further, the page does, near the screen's own edge.
 */

/** How close to an edge (px) the scrolling starts. */
export const EDGE_ZONE_PX = 48;
/** The fastest scroll, in px a frame (about 1 000 px a second at 60 frames). */
export const MAX_STEP_PX = 18;

export interface Box {
  left: number;
  top: number;
  right: number;
  bottom: number;
}

export interface Point {
  x: number;
  y: number;
}

export interface Step {
  dx: number;
  dy: number;
}

/** The scroll step along one axis for a pointer at `position` between `start` and `end`; negative scrolls toward the start. */
export function edgeStep(position: number, start: number, end: number, zone = EDGE_ZONE_PX, max = MAX_STEP_PX): number {
  const size = end - start;
  if (!(size > 0)) {
    return 0;
  }
  // A small box keeps a middle where nothing scrolls.
  const reach = Math.min(zone, size / 4);
  const speed = (depth: number) => Math.max(1, Math.round(max * Math.min(1, depth / reach)));
  if (position < start + reach) {
    return -speed(start + reach - position);
  }
  if (position > end - reach) {
    return speed(position - (end - reach));
  }
  return 0;
}

/** The part of `box` on screen. */
export function visibleBox(box: Box, viewport: { width: number; height: number }): Box {
  return {
    left: Math.max(box.left, 0),
    top: Math.max(box.top, 0),
    right: Math.min(box.right, viewport.width),
    bottom: Math.min(box.bottom, viewport.height),
  };
}

/** How far to scroll a box this frame for a pointer at `pointer`. */
export function autoScrollStep(pointer: Point, box: Box): Step {
  return { dx: edgeStep(pointer.x, box.left, box.right), dy: edgeStep(pointer.y, box.top, box.bottom) };
}
