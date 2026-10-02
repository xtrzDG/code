/**
 * The numbers on Messages in the sidebar, the phone tab bar and the
 * Messages tabs: conversations waiting for a person and new requests.
 */

import type { BusinessPage } from "./navigation";
import type { BusinessSection } from "./sections";

export interface InboxCounts {
  /** Handoffs nobody has resolved yet. */
  openHandoffs: number;
  /** Requests (leads) still in the "new" status. */
  newLeads: number;
}

/** The largest number a badge spells out; more shows as "99+". */
export const BADGE_LIMIT = 99;

/** The badge of a page, 0 for none. */
export function pageBadge(page: BusinessPage, counts: InboxCounts | null): number {
  if (!counts) {
    return 0;
  }
  if (page === "messages/handoffs") {
    return counts.openHandoffs;
  }
  return page === "messages/leads" ? counts.newLeads : 0;
}

/** The badge of a section: everything waiting in its pages. */
export function sectionBadge(section: BusinessSection, counts: InboxCounts | null): number {
  return section === "messages" && counts ? counts.openHandoffs + counts.newLeads : 0;
}

/** What the badge shows: "7", "99+". */
export function badgeText(count: number): string {
  return count > BADGE_LIMIT ? `${BADGE_LIMIT}+` : String(count);
}
