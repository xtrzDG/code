import { describe, expect, it } from "vitest";

import {
  bannerAnnouncements,
  canDismiss,
  dismissKey,
  goodDayShare,
  parseDismissed,
  type Announcement,
  type PlatformStatus,
} from "./platformStatus";

function announcement(id: string, level: Announcement["level"], updatedAt = 1): Announcement {
  return {
    id,
    level,
    components: level === "info" ? [] : ["chat"],
    text: `Text ${id}`,
    language: "en",
    starts_at: 1,
    updated_at: updatedAt,
    is_scheduled: false,
    expected_end_at: null,
    resolved_at: null,
  };
}

function status(announcements: Announcement[]): PlatformStatus {
  return { level: "operational", checked_at: 1, components: [], announcements, past_announcements: [] };
}

describe("goodDayShare", () => {
  it("counts days that worked or were planned maintenance", () => {
    expect(
      goodDayShare([
        { day: "2026-10-01", level: "operational" },
        { day: "2026-10-02", level: "maintenance" },
        { day: "2026-10-03", level: "degraded" },
        { day: "2026-10-04", level: "outage" },
        { day: "2026-10-05", level: "no_data" },
      ]),
    ).toBe(0.5);
  });

  it("has nothing to say before a day is measured", () => {
    expect(goodDayShare([{ day: "2026-10-01", level: "no_data" }])).toBeNull();
    expect(goodDayShare([])).toBeNull();
  });
});

describe("the banner", () => {
  it("shows the most serious announcement first, then the latest", () => {
    const shown = bannerAnnouncements(
      status([announcement("a", "info", 5), announcement("b", "outage"), announcement("c", "info", 9)]),
      [],
    );
    expect(shown.map((item) => item.id)).toEqual(["b", "c", "a"]);
  });

  it("leaves out hidden announcements until they change, but never an outage", () => {
    const degraded = announcement("d", "degraded", 3);
    const outage = announcement("o", "outage", 4);
    const hidden = [dismissKey(degraded), dismissKey(outage)];
    expect(bannerAnnouncements(status([degraded, outage]), hidden).map((item) => item.id)).toEqual(["o"]);
    expect(bannerAnnouncements(status([{ ...degraded, updated_at: 7 }]), hidden).map((item) => item.id)).toEqual(["d"]);
    expect(canDismiss(outage)).toBe(false);
    expect(canDismiss(degraded)).toBe(true);
  });

  it("shows nothing before the status is loaded", () => {
    expect(bannerAnnouncements(undefined, [])).toEqual([]);
  });

  it("reads the hidden banners kept in the browser", () => {
    expect(parseDismissed(JSON.stringify(["a@1", 2, "b@3"]))).toEqual(["a@1", "b@3"]);
    expect(parseDismissed("{")).toEqual([]);
    expect(parseDismissed(JSON.stringify({ a: 1 }))).toEqual([]);
    expect(parseDismissed(null)).toEqual([]);
  });
});
