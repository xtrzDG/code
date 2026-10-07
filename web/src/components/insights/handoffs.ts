/** Ordering and state of handoffs (used by the handoffs page and the dashboard). */

import type { HandoffListItem, HandoffUrgency } from "./types";

const URGENCY_RANK: Record<HandoffUrgency, number> = { critical: 0, high: 1, normal: 2, low: 3 };

/** A handoff still waits for a person until staff resolve it. */
export function isOpenHandoff(handoff: Pick<HandoffListItem, "status">): boolean {
  return handoff.status !== "resolved";
}

/**
 * Open handoffs first, the most urgent first, then the oldest first (it has
 * waited longest); resolved ones after them, the most recently resolved first.
 */
export function sortHandoffs<T extends Pick<HandoffListItem, "status" | "urgency" | "created_at" | "resolved_at">>(
  handoffs: readonly T[],
): T[] {
  return [...handoffs].sort((left, right) => {
    const leftOpen = isOpenHandoff(left);
    const rightOpen = isOpenHandoff(right);
    if (leftOpen !== rightOpen) {
      return leftOpen ? -1 : 1;
    }
    if (leftOpen) {
      const byUrgency = URGENCY_RANK[left.urgency] - URGENCY_RANK[right.urgency];
      return byUrgency !== 0 ? byUrgency : left.created_at - right.created_at;
    }
    return (right.resolved_at ?? right.created_at) - (left.resolved_at ?? left.created_at);
  });
}
