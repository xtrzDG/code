import { describe, expect, it } from "vitest";

import { BADGE_LIMIT, badgeText, pageBadge, sectionBadge, titleWithCount } from "./inboxBadges";

const counts = { openHandoffs: 3, newLeads: 2, unconfirmedBookings: 4, channelErrors: 1 };

describe("attention badges", () => {
  it("put each waiting item on its page", () => {
    // The inbox waits on people asked for and new requests together.
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
