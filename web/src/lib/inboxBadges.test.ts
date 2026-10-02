import { describe, expect, it } from "vitest";

import { BADGE_LIMIT, badgeText, pageBadge, sectionBadge } from "./inboxBadges";

const counts = { openHandoffs: 3, newLeads: 2 };

describe("inbox badges", () => {
  it("put open handoffs and new requests on their pages", () => {
    expect(pageBadge("messages/handoffs", counts)).toBe(3);
    expect(pageBadge("messages/leads", counts)).toBe(2);
    expect(pageBadge("messages", counts)).toBe(0);
    expect(pageBadge("messages/leads", null)).toBe(0);
  });

  it("add them up on Messages only", () => {
    expect(sectionBadge("messages", counts)).toBe(5);
    expect(sectionBadge("bookings", counts)).toBe(0);
    expect(sectionBadge("messages", null)).toBe(0);
  });

  it("spell out at most two digits", () => {
    expect(badgeText(7)).toBe("7");
    expect(badgeText(BADGE_LIMIT)).toBe("99");
    expect(badgeText(BADGE_LIMIT + 1)).toBe("99+");
  });
});
