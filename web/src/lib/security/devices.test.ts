import { describe, expect, it } from "vitest";

import type { UserSessionView } from "@/api/types";

import { onlyCurrent, otherSessionCount, sortSessions, withoutSession } from "./devices";

function session(id: string, lastSeen: number, isCurrent = false): UserSessionView {
  return {
    id,
    device: { kind: "desktop", browser: "Chrome", operating_system: "macOS" },
    auth_level: "one_factor",
    created_at: 1,
    last_seen_at: lastSeen,
    expires_at: 10,
    is_current: isCurrent,
  };
}

describe("signed-in devices", () => {
  const items = [session("old", 100), session("here", 50, true), session("recent", 300)];

  it("lists this device first, then the most recently used", () => {
    expect(sortSessions(items).map((item) => item.id)).toEqual(["here", "recent", "old"]);
  });

  it("counts and removes the other devices", () => {
    expect(otherSessionCount(items)).toBe(2);
    expect(withoutSession(items, "old").map((item) => item.id)).toEqual(["here", "recent"]);
    expect(onlyCurrent(items).map((item) => item.id)).toEqual(["here"]);
  });
});
