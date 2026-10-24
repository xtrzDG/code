import { describe, expect, it } from "vitest";

import type { SupportAccessView } from "@/api/types";

import { isSupportPresent, supportUntil } from "./supportAccess";

function view(sessions: number[], isAllowed = false): SupportAccessView {
  return {
    sessions: sessions.map((expiresAt, index) => ({
      grant_id: `support_access_${index}`,
      reason: "Owner asked why bookings stopped",
      started_at: 1,
      expires_at: expiresAt,
      is_yours: false,
    })),
    write_access: { is_allowed: isAllowed },
    is_support_viewer: false,
    viewer_can_write: false,
  };
}

describe("support access banner", () => {
  it("shows while support looks in or may make changes", () => {
    expect(isSupportPresent(undefined)).toBe(false);
    expect(isSupportPresent(view([]))).toBe(false);
    expect(isSupportPresent(view([100]))).toBe(true);
    expect(isSupportPresent(view([], true))).toBe(true);
  });

  it("names when the last look ends", () => {
    expect(supportUntil(view([100, 300, 200]))).toBe(300);
    expect(supportUntil(view([]))).toBeNull();
  });
});
