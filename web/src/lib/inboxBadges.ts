/**
 * The numbers on the navigation (sidebar, phone tab bar, section tabs) and
 * in the browser tab's title: what waits for a person, from GET
 * …/attention-counts, kept fresh by the live event stream.
 */

import type { BusinessPage } from "./navigation";

export interface AttentionCounts {
  /** Handoffs nobody has resolved yet. */
  openHandoffs: number;
  /** Requests (leads) still in the "new" status. */
  newLeads: number;
  /** Pending bookings that have not started yet. */
  unconfirmedBookings: number;
  /** Channels the platform refused (owners fix them). */
  channelErrors: number;
}

/** The largest number a badge spells out; more shows as "99+". */
export const BADGE_LIMIT = 99;

/** The badge of a page, 0 for none. */
export function pageBadge(page: BusinessPage, counts: AttentionCounts | null): number {
  if (!counts) {
    return 0;
  }
  switch (page) {
    case "inbox":
      // Everything that waits for the team: people asked for, new requests.
      return counts.openHandoffs + counts.newLeads;
    case "bookings":
      return counts.unconfirmedBookings;
    case "assistant/channels":
      return counts.channelErrors;
    default:
      return 0;
  }
}

/** The badge of a section: everything waiting on the pages the person sees in it. */
export function sectionBadge(pages: readonly BusinessPage[], counts: AttentionCounts | null): number {
  return pages.reduce((total, page) => total + pageBadge(page, counts), 0);
}

/** What the badge shows: "7", "99+". */
export function badgeText(count: number): string {
  return count > BADGE_LIMIT ? `${BADGE_LIMIT}+` : String(count);
}

const COUNT_PREFIX = /^\(\d+\+?\) /;

/** The tab title with what waits in front: "(3) Bookings · Salobie". */
export function titleWithCount(title: string, count: number): string {
  const bare = title.replace(COUNT_PREFIX, "");
  return count > 0 ? `(${badgeText(count)}) ${bare}` : bare;
}
