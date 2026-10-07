"use client";

import { useEffect, useRef, useState, type KeyboardEvent, type MouseEvent, type PointerEvent } from "react";

import type { BookingView } from "@/components/insights/types";

import { isSameSpot, keyboardTarget, placeOf, type MovePlace } from "./_lib/calendarMoves";
import type { MoveTarget } from "./_lib/calendarTypes";
import type { Point } from "./_lib/edgeScroll";
import { useEdgeAutoScroll } from "./useEdgeAutoScroll";

/** A mouse or pen drags once it moved this far (px); less is a click. */
const DRAG_THRESHOLD = 4;
/** A finger that moves this far before the long press is scrolling. */
const TOUCH_SLOP = 8;
/** A finger drags after holding a booking this long (ms), so a swipe still scrolls. */
const LONG_PRESS_MS = 350;

/** Where the grabbed booking would land with the pointer at (x, y) on screen; null outside the grid. */
export type Locate = (x: number, y: number) => MoveTarget | null;

/** The booking being moved and where it would land: following the pointer, or waiting for Enter. */
export interface MovePreview {
  booking: BookingView;
  target: MoveTarget;
  source: "drag" | "keys";
}

interface Session {
  booking: BookingView;
  locate: Locate;
  pointerId: number;
  startX: number;
  startY: number;
  isActive: boolean;
  timer: ReturnType<typeof setTimeout> | null;
}

const sameTarget = (a: MoveTarget, b: MoveTarget) => a.resourceId === b.resourceId && a.date === b.date && a.time === b.time;

function focusBooking(id: string) {
  requestAnimationFrame(() => {
    document.querySelector<HTMLElement>(`[data-calendar-booking="${CSS.escape(id)}"]`)?.focus();
  });
}

/**
 * Moving bookings on a grid by pointer and by keyboard. A mouse drags at
 * once, a finger after a long press; the drop calls `onMove`. Near an edge
 * of the grid (`scroller`) a drag scrolls it that way (useEdgeAutoScroll),
 * and the drop target follows what comes under the pointer. With the
 * keyboard, the arrows move the focused booking's preview a step at a time
 * (`keyboardTarget`), Enter moves it there and Escape (or leaving it)
 * cancels. Escape also cancels a drag. A drag never ends in a click.
 */
export function useMoveGestures({
  onMove,
  places,
  bounds,
  forwardKey,
  scroller,
  moves = "time",
}: {
  onMove: (booking: BookingView, target: MoveTarget) => Promise<boolean>;
  /** The grid's scrolling box, scrolled while a booking is dragged near its edges. */
  scroller: () => HTMLElement | null;
  /** "time": a booking moves by quarters of an hour; "nights": a stay moves by nights. */
  moves?: "time" | "nights";
  places: readonly MovePlace[];
  bounds: { firstMinute: number; lastMinute: number; firstDate: string; lastDate: string };
  /** The arrow that points to the next place in reading order ("ArrowLeft" right to left). */
  forwardKey: "ArrowRight" | "ArrowLeft";
}) {
  const [preview, setPreview] = useState<MovePreview | null>(null);
  const origin = (booking: BookingView) => placeOf(booking, moves === "nights");
  const [isCancelled, setCancelled] = useState(false);
  const session = useRef<Session | null>(null);
  const suppressClick = useRef(false);
  const pointer = useRef<Point | null>(null);
  const isDragging = preview?.source === "drag";

  /** The drop target under the pointer at (x, y), as the preview shows it. */
  const follow = (current: Session, x: number, y: number) => {
    const target = current.locate(x, y) ?? origin(current.booking);
    setPreview((shown) =>
      shown?.source === "drag" && sameTarget(shown.target, target) ? shown : { booking: current.booking, target, source: "drag" },
    );
  };

  useEdgeAutoScroll({
    active: isDragging,
    scroller,
    pointer,
    onScrolled: (at) => {
      if (session.current?.isActive) {
        follow(session.current, at.x, at.y);
      }
    },
  });

  // While dragging: a finger does not scroll the page, and Escape drops nothing.
  useEffect(() => {
    if (!isDragging) {
      return;
    }
    const holdStill = (event: TouchEvent) => event.preventDefault();
    const escape = (event: globalThis.KeyboardEvent) => {
      if (event.key === "Escape") {
        session.current = null;
        setPreview(null);
        setCancelled(true);
      }
    };
    document.addEventListener("touchmove", holdStill, { passive: false });
    window.addEventListener("keydown", escape);
    return () => {
      document.removeEventListener("touchmove", holdStill);
      window.removeEventListener("keydown", escape);
    };
  }, [isDragging]);

  const endSession = () => {
    const current = session.current;
    if (current?.timer) {
      clearTimeout(current.timer);
    }
    session.current = null;
  };

  const activate = (current: Session, x: number, y: number) => {
    current.isActive = true;
    pointer.current = { x, y };
    suppressClick.current = true;
    setCancelled(false);
    setPreview({ booking: current.booking, target: current.locate(x, y) ?? origin(current.booking), source: "drag" });
  };

  const commit = (booking: BookingView, target: MoveTarget, source: MovePreview["source"]) => {
    setPreview(null);
    if (isSameSpot(booking, target)) {
      return;
    }
    void onMove(booking, target);
    if (source === "keys") {
      focusBooking(booking.id);
    }
  };

  /** The props that make one booking (a block of the day, a bar of the nights) movable. */
  const movable = (booking: BookingView, makeLocate: (event: PointerEvent<HTMLElement>) => Locate) => ({
    "data-calendar-booking": booking.id,
    onPointerDown: (event: PointerEvent<HTMLElement>) => {
      suppressClick.current = false;
      if (!event.isPrimary || (event.pointerType === "mouse" && event.button !== 0)) {
        return;
      }
      const current: Session = {
        booking,
        locate: makeLocate(event),
        pointerId: event.pointerId,
        startX: event.clientX,
        startY: event.clientY,
        isActive: false,
        timer: null,
      };
      endSession();
      session.current = current;
      if (event.pointerType === "touch") {
        current.timer = setTimeout(() => {
          if (session.current === current) {
            activate(current, current.startX, current.startY);
          }
        }, LONG_PRESS_MS);
      } else {
        event.currentTarget.setPointerCapture(event.pointerId);
      }
    },
    onPointerMove: (event: PointerEvent<HTMLElement>) => {
      const current = session.current;
      if (!current || current.pointerId !== event.pointerId) {
        return;
      }
      if (!current.isActive) {
        const distance = Math.hypot(event.clientX - current.startX, event.clientY - current.startY);
        if (event.pointerType === "touch") {
          if (distance > TOUCH_SLOP) {
            endSession();
          }
        } else if (distance >= DRAG_THRESHOLD) {
          activate(current, event.clientX, event.clientY);
        }
        return;
      }
      pointer.current = { x: event.clientX, y: event.clientY };
      follow(current, event.clientX, event.clientY);
    },
    onPointerUp: (event: PointerEvent<HTMLElement>) => {
      const current = session.current;
      if (!current || current.pointerId !== event.pointerId) {
        return;
      }
      endSession();
      if (current.isActive) {
        commit(current.booking, current.locate(event.clientX, event.clientY) ?? origin(current.booking), "drag");
        // The click that ends a drag is swallowed; when the moved block left the page none comes.
        setTimeout(() => {
          suppressClick.current = false;
        }, 0);
      }
    },
    onPointerCancel: () => {
      const wasActive = session.current?.isActive ?? false;
      endSession();
      if (wasActive) {
        setPreview(null);
      }
    },
    onContextMenu: (event: MouseEvent<HTMLElement>) => {
      // A long press on a phone grabs the booking instead of opening the menu.
      if (session.current) {
        event.preventDefault();
      }
    },
    onClickCapture: (event: MouseEvent<HTMLElement>) => {
      if (suppressClick.current) {
        suppressClick.current = false;
        event.preventDefault();
        event.stopPropagation();
      }
    },
    onKeyDown: (event: KeyboardEvent<HTMLElement>) => {
      const pending = preview?.source === "keys" && preview.booking.id === booking.id ? preview : null;
      if (event.key === "Enter" && pending) {
        event.preventDefault();
        commit(booking, pending.target, "keys");
        return;
      }
      if (event.key === "Escape" && pending) {
        event.preventDefault();
        event.stopPropagation();
        setPreview(null);
        setCancelled(true);
        return;
      }
      if (!event.key.startsWith("Arrow")) {
        return;
      }
      event.preventDefault();
      const next = keyboardTarget(pending?.target ?? origin(booking), event.key, places, bounds, forwardKey);
      if (next) {
        setCancelled(false);
        setPreview(isSameSpot(booking, next) ? null : { booking, target: next, source: "keys" });
      }
    },
    onBlur: () => {
      setPreview((shown) => (shown?.source === "keys" && shown.booking.id === booking.id ? null : shown));
    },
  });

  return { preview, isCancelled, movable };
}
