"use client";

/**
 * A panel anchored to a control (a date field's calendar). It opens in the
 * browser's top layer (`popover="manual"`), so no scrolling card or dialog
 * clips it, and sits under the anchor, or above it when there is more room
 * there, kept inside the viewport. A press outside the panel and its
 * anchor closes it; Escape is the content's to handle (a calendar closes on
 * it and gives the focus back).
 */

import { useCallback, useEffect, useLayoutEffect, useRef, useState, type ReactNode, type RefObject } from "react";

import { cn } from "@/lib/cn";

const GAP_PX = 6;

/** Whether this browser has the top layer for popovers (opened only after a click, so never on the server). */
function hasTopLayer(): boolean {
  return typeof HTMLElement !== "undefined" && typeof HTMLElement.prototype.showPopover === "function";
}
const EDGE_PX = 8;

interface Placement {
  top: number;
  left: number;
}

/** Where a panel of `size` goes next to `anchor` in a viewport of `viewport` (both in CSS pixels). */
export function placePopover(
  anchor: Pick<DOMRect, "top" | "bottom" | "left" | "right">,
  size: { width: number; height: number },
  viewport: { width: number; height: number },
  direction: "ltr" | "rtl" = "ltr",
): Placement {
  const below = anchor.bottom + GAP_PX;
  const roomBelow = viewport.height - below - EDGE_PX;
  const roomAbove = anchor.top - GAP_PX - EDGE_PX;
  const top = size.height <= roomBelow || roomBelow >= roomAbove ? below : Math.max(EDGE_PX, anchor.top - GAP_PX - size.height);
  const start = direction === "rtl" ? anchor.right - size.width : anchor.left;
  const left = Math.min(Math.max(EDGE_PX, start), Math.max(EDGE_PX, viewport.width - size.width - EDGE_PX));
  return { top: Math.round(top), left: Math.round(left) };
}

export function Popover({
  anchor,
  onClose,
  label,
  className,
  children,
}: {
  anchor: RefObject<HTMLElement | null>;
  onClose: () => void;
  label: string;
  className?: string;
  children: ReactNode;
}) {
  const panel = useRef<HTMLDivElement>(null);
  const [placement, setPlacement] = useState<Placement | null>(null);
  const closeRef = useRef(onClose);
  useEffect(() => {
    closeRef.current = onClose;
  });

  const place = useCallback(() => {
    const element = panel.current;
    const target = anchor.current;
    if (!element || !target) {
      return;
    }
    const direction = getComputedStyle(target).direction === "rtl" ? "rtl" : "ltr";
    setPlacement(
      placePopover(
        target.getBoundingClientRect(),
        { width: element.offsetWidth, height: element.offsetHeight },
        { width: window.innerWidth, height: window.innerHeight },
        direction,
      ),
    );
  }, [anchor]);

  useLayoutEffect(() => {
    const element = panel.current;
    if (element && typeof element.showPopover === "function") {
      try {
        if (!element.matches(":popover-open")) {
          element.showPopover();
        }
      } catch {
        // An engine without the top layer shows the panel where it is.
      }
    }
    place();
  }, [place]);

  useEffect(() => {
    const onPointer = (event: PointerEvent) => {
      const target = event.target as Node;
      if (!panel.current?.contains(target) && !anchor.current?.contains(target)) {
        closeRef.current();
      }
    };
    document.addEventListener("pointerdown", onPointer);
    window.addEventListener("resize", place);
    window.addEventListener("scroll", place, true);
    return () => {
      document.removeEventListener("pointerdown", onPointer);
      window.removeEventListener("resize", place);
      window.removeEventListener("scroll", place, true);
    };
  }, [anchor, place]);

  return (
    <div
      ref={panel}
      popover={hasTopLayer() ? "manual" : undefined}
      role="dialog"
      aria-label={label}
      style={placement ? { top: placement.top, left: placement.left } : { top: 0, left: 0, visibility: "hidden" }}
      className={cn(
        "animate-settle fixed inset-auto z-50 m-0 overflow-visible rounded-xl border border-line bg-surface p-3 text-ink shadow-2xl",
        className,
      )}
    >
      {children}
    </div>
  );
}
