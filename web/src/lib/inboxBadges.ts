/**
 * The numbers on the navigation (sidebar, phone tab bar, section tabs) and
 * in the browser tab's title: what waits for a person, from GET
 * …/attention-counts, kept fresh by the live event stream. The API counts
 * them once (the same numbers as the inbox tabs, GET …/inbox/counts), so a
 * badge never disagrees with the tabs it sums.
 */

import type { Schema } from "@/api/types";

import type { BusinessPage } from "./navigation";

export interface AttentionCounts {
  /** Conversations that need a person (the inbox tab "Needs a person"). */
  needsPerson: number;
  /** Conversations with an open request (the inbox tab "Requests"). */
  requests: number;
  /** Waiting conversations nobody is assigned to. */
  unassigned: number;
  /** Waiting conversations assigned to the viewer. */
  mine: number;
  /** Pending bookings that have not started yet. */
  unconfirmedBookings: number;
  /** Channels the platform refused (owners fix them). */
  channelErrors: number;
}

/** The API's counts as the cabinet keeps them. */
export function attentionCountsFrom(data: Schema<"InboxAttentionCounts">): AttentionCounts {
  return {
    needsPerson: data.needs_person,
    requests: data.requests,
    unassigned: data.unassigned,
    mine: data.mine,
    unconfirmedBookings: data.unconfirmed_bookings,
    channelErrors: data.channel_errors,
  };
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
      // The sum of the two inbox tabs that wait for the team.
      return counts.needsPerson + counts.requests;
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

/**
 * Everything waiting for this person, for the browser tab's title: the inbox,
 * bookings to confirm and, for those who may open Channels, channels in error.
 */
export function waitingTotal(counts: AttentionCounts | null, canSeeChannels: boolean): number {
  if (!counts) {
    return 0;
  }
  return pageBadge("inbox", counts) + counts.unconfirmedBookings + (canSeeChannels ? counts.channelErrors : 0);
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
