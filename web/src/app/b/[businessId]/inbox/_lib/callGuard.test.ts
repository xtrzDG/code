import { describe, expect, it } from "vitest";

import { callGuardBadge, callGuardFindings } from "./callGuard";

describe("the after-call check on the conversation card", () => {
  it("labels a checked call and leaves an unchecked one alone", () => {
    expect(callGuardBadge({ guard_verdict: "clean" })).toEqual({
      tone: "success",
      label: "conversations.calls.guard.clean",
    });
    expect(callGuardBadge({ guard_verdict: "handed_off" })?.tone).toBe("warning");
    expect(callGuardBadge({ guard_verdict: null })).toBeNull();
    expect(callGuardBadge({})).toBeNull();
  });

  it("lists the values not found in the data, with the right title", () => {
    expect(callGuardFindings({ guard_verdict: "flagged", unverified_values: ["30 lari"] })).toEqual({
      title: "conversations.calls.guard.flaggedTitle",
      values: ["30 lari"],
    });
    expect(callGuardFindings({ guard_verdict: "handed_off", unverified_values: ["30 lari", "21:30"] })).toEqual({
      title: "conversations.calls.guard.handedOffTitle",
      values: ["30 lari", "21:30"],
    });
  });

  it("shows no warning for a clean call or one without values", () => {
    expect(callGuardFindings({ guard_verdict: "clean", unverified_values: [] })).toBeNull();
    expect(callGuardFindings({ guard_verdict: "flagged", unverified_values: [] })).toBeNull();
    expect(callGuardFindings({ guard_verdict: null })).toBeNull();
  });
});
