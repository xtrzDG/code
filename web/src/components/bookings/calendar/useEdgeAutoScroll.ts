"use client";

import { useEffect, useRef, type RefObject } from "react";

import { autoScrollStep, visibleBox, type Point } from "./_lib/edgeScroll";

/** Scrolls `element` by the step; true when it moved. */
function scrollBy(element: Element, dx: number, dy: number): boolean {
  const left = element.scrollLeft;
  const top = element.scrollTop;
  element.scrollBy({ left: dx, top: dy, behavior: "instant" });
  return element.scrollLeft !== left || element.scrollTop !== top;
}

/**
 * While `active` (a booking is being dragged), every animation frame
 * scrolls the grid toward the edge the pointer is near (edgeScroll.ts), on
 * both axes, mouse or finger alike; where the grid is at its end, the page
 * scrolls near the screen's edge. After a scroll `onScrolled` gets the
 * pointer, so the drop target follows what is now under it.
 */
export function useEdgeAutoScroll({
  active,
  scroller,
  pointer,
  onScrolled,
}: {
  active: boolean;
  scroller: () => HTMLElement | null;
  /** The pointer's last position on screen, kept by the drag. */
  pointer: RefObject<Point | null>;
  onScrolled: (at: Point) => void;
}) {
  const latest = useRef({ scroller, onScrolled });
  useEffect(() => {
    latest.current = { scroller, onScrolled };
  });

  useEffect(() => {
    if (!active) {
      return undefined;
    }
    let frame = 0;
    const tick = () => {
      const element = latest.current.scroller();
      const at = pointer.current;
      if (element && at) {
        const viewport = { width: window.innerWidth, height: window.innerHeight };
        const step = autoScrollStep(at, visibleBox(element.getBoundingClientRect(), viewport));
        let moved = (step.dx !== 0 || step.dy !== 0) && scrollBy(element, step.dx, step.dy);
        const page = document.scrollingElement;
        if (!moved && page) {
          const edge = autoScrollStep(at, { left: 0, top: 0, right: viewport.width, bottom: viewport.height });
          moved = (edge.dx !== 0 || edge.dy !== 0) && scrollBy(page, edge.dx, edge.dy);
        }
        if (moved) {
          latest.current.onScrolled(at);
        }
      }
      frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [active, pointer]);
}
