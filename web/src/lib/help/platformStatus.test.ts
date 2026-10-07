import { describe, expect, it } from "vitest";

import {
  bannerAnnouncements,
  canDismiss,
  dismissKey,
  historySummary,
  minutesSinceCheck,
  parseDismissed,
  type Announcement,
  type PlatformStatus,
  type StatusDay,
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
  return { level: "operational", checked_at: 1, monitoring_delayed: false, components: [], announcements, past_announcements: [] };
}

function days(levels: readonly StatusDay["level"][], start = 1): StatusDay[] {
  return levels.map((level, index) => ({ day: `2026-09-${String(start + index).padStart(2, "0")}`, level }));
}

describe("historySummary", () => {
  it("counts from the first recorded day, not from the start of the 90 bars", () => {
    const history = [...days(["no_data", "no_data", "no_data"]), ...days(Array(7).fill("operational"), 4)];
    expect(historySummary(history)).toEqual({ kind: "share", share: 1, days: 7 });
  });

  it("says since when it observes until a week is measured", () => {
    // One measured day never reads as "100 %"; one slow day never as "0 %".
    expect(historySummary(days(["no_data", "operational"]))).toEqual({ kind: "observing", since: "2026-09-02" });
    expect(historySummary(days(["degraded"]))).toEqual({ kind: "observing", since: "2026-09-01" });
    expect(historySummary(days(["operational", "operational", "operational", "operational", "operational", "operational", "no_data"]))).toEqual({
      kind: "observing",
      since: "2026-09-01",
    });
  });

  it("counts a degraded day as half, an outage and an unrecorded day after the first as none", () => {
    const history = days(["operational", "maintenance", "degraded", "outage", "no_data", "operational", "operational", "operational"]);
    expect(historySummary(history)).toEqual({ kind: "share", share: 5.5 / 8, days: 8 });
  });

  it("does not count today while it has no record yet", () => {
    const history = days([...Array(8).fill("operational"), "no_data"]);
    expect(historySummary(history)).toEqual({ kind: "share", share: 1, days: 8 });
  });

  it("has nothing to say before a day is measured", () => {
    expect(historySummary(days(["no_data"]))).toEqual({ kind: "none" });
    expect(historySummary([])).toEqual({ kind: "none" });
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

describe("minutesSinceCheck", () => {
  const checkedAt = Date.UTC(2026, 9, 6, 12, 0) * 1000;

  it("counts whole minutes since the last check", () => {
    expect(minutesSinceCheck(checkedAt, Date.UTC(2026, 9, 6, 12, 17, 59))).toBe(17);
    expect(minutesSinceCheck(checkedAt, Date.UTC(2026, 9, 6, 12, 0, 30))).toBe(0);
  });

  it("reads a browser clock behind the server's as no time at all", () => {
    expect(minutesSinceCheck(checkedAt, Date.UTC(2026, 9, 6, 11, 58))).toBe(0);
  });
});
