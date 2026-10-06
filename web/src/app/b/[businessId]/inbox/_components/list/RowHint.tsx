"use client";

/**
 * The details a row no longer shows on its face (who handles it, where the
 * customer came from, after hours, notes, the exact time), in a small card
 * beside the row after the pointer rests on it or the keyboard lands on it.
 *
 * The card lives in the top layer (`popover="manual"`), so the list's
 * scrolling box never clips it; it sits beside the list column, or under
 * the row where there is no room. Screen readers already hear the same
 * details inside the row's link, so the card is hidden from them. Phones
 * (no hover) open the conversation instead.
 */

import { useEffect, useRef, useState } from "react";

import type { InboxRow } from "../../_lib/inboxModel";
import type { TeamMember } from "../../_lib/team";
import { RowDetails } from "./rowParts";

/** How long the pointer or the focus rests on a row before its card shows. */
const SHOW_AFTER_MS = 450;
const CARD_WIDTH = 264;
const GAP = 8;

export interface HintTarget {
  row: InboxRow;
  element: HTMLElement;
}

function placeCard(card: HTMLElement, anchor: DOMRect): void {
  const roomBeside = window.innerWidth - anchor.right - GAP;
  const height = card.offsetHeight;
  if (roomBeside >= CARD_WIDTH + GAP) {
    card.style.left = `${anchor.right + GAP}px`;
    card.style.top = `${Math.max(GAP, Math.min(anchor.top, window.innerHeight - height - GAP))}px`;
  } else {
    card.style.left = `${Math.max(GAP, Math.min(anchor.left + 16, window.innerWidth - CARD_WIDTH - GAP))}px`;
    const below = anchor.bottom + 4;
    card.style.top = `${below + height > window.innerHeight - GAP ? Math.max(GAP, anchor.top - height - 4) : below}px`;
  }
}

function canHover(): boolean {
  return typeof window !== "undefined" && window.matchMedia("(hover: hover)").matches;
}

export function RowHint({ target, memberOf }: { target: HintTarget | null; memberOf: (userId: string | null | undefined) => TeamMember | null }) {
  const card = useRef<HTMLDivElement>(null);
  // The target the pointer or focus has rested on long enough; leaving it hides the card at once.
  const [rested, setRested] = useState<HintTarget | null>(null);
  const shown = target !== null && rested === target ? target : null;

  useEffect(() => {
    if (target === null || !canHover()) {
      return;
    }
    const timer = window.setTimeout(() => setRested(target), SHOW_AFTER_MS);
    return () => window.clearTimeout(timer);
  }, [target]);

  useEffect(() => {
    const element = card.current;
    if (!element || typeof element.showPopover !== "function") {
      return;
    }
    if (shown === null || !shown.element.isConnected) {
      if (element.matches(":popover-open")) {
        element.hidePopover();
      }
      return;
    }
    if (!element.matches(":popover-open")) {
      element.showPopover();
    }
    placeCard(element, shown.element.getBoundingClientRect());
    // Scrolling moves the row away from its card: hide it.
    const hide = () => setRested(null);
    window.addEventListener("scroll", hide, { capture: true, passive: true });
    window.addEventListener("resize", hide);
    return () => {
      window.removeEventListener("scroll", hide, { capture: true });
      window.removeEventListener("resize", hide);
    };
  }, [shown]);

  return (
    <div
      ref={card}
      popover="manual"
      aria-hidden
      data-row-hint=""
      style={{ width: CARD_WIDTH }}
      className="pointer-events-none fixed m-0 inset-auto rounded-xl border border-line bg-surface px-3.5 py-3 text-xs text-ink shadow-xl"
    >
      {shown ? <RowDetails row={shown.row} member={memberOf(shown.row.assigneeUserId)} /> : null}
    </div>
  );
}
