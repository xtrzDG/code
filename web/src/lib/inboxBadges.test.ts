import { describe, expect, it } from "vitest";

import { attentionCountsFrom, BADGE_LIMIT, badgeText, pageBadge, sectionBadge, titleWithCount, waitingTotal } from "./inboxBadges";

const counts = { needsPerson: 3, requests: 2, unassigned: 4, mine: 1, unconfirmedBookings: 4, channelErrors: 1 };

describe("attention badges", () => {
  it("put each waiting item on its page", () => {
    // The inbox badge is the sum of its two waiting tabs, nothing else.
    expect(pageBadge("inbox", counts)).toBe(5);
    expect(pageBadge("bookings", counts)).toBe(4);
    expect(pageBadge("assistant/channels", counts)).toBe(1);
    expect(pageBadge("overview", counts)).toBe(0);
    expect(pageBadge("inbox", null)).toBe(0);
  });

  it("add up the pages a person sees in a section", () => {
    expect(sectionBadge(["inbox"], counts)).toBe(5);
    expect(sectionBadge(["assistant", "assistant/channels"], counts)).toBe(1);
    expect(sectionBadge(["assistant"], counts)).toBe(0);
    expect(sectionBadge(["bookings"], null)).toBe(0);
  });

  it("read the API's counts under the cabinet's names", () => {
    expect(
      attentionCountsFrom({
        business_id: "business_1",
        needs_person: 3,
        requests: 2,
        unassigned: 4,
        mine: 1,
        unconfirmed_bookings: 4,
        channel_errors: 1,
        open_handoff_count: 3,
        new_lead_count: 2,
        unconfirmed_booking_count: 4,
        channel_error_count: 1,
      }),
    ).toEqual(counts);
  });

  it("count everything waiting for the tab title, channels only for those who see them", () => {
    expect(waitingTotal(counts, true)).toBe(10);
    expect(waitingTotal(counts, false)).toBe(9);
    expect(waitingTotal(null, true)).toBe(0);
  });

  it("spell out at most two digits", () => {
    expect(badgeText(7)).toBe("7");
    expect(badgeText(BADGE_LIMIT)).toBe("99");
    expect(badgeText(BADGE_LIMIT + 1)).toBe("99+");
  });

  it("put the count in front of the tab title, once", () => {
    expect(titleWithCount("Bookings · Salobie", 3)).toBe("(3) Bookings · Salobie");
    expect(titleWithCount("(3) Bookings · Salobie", 120)).toBe("(99+) Bookings · Salobie");
    expect(titleWithCount("(99+) Bookings · Salobie", 0)).toBe("Bookings · Salobie");
  });
});
