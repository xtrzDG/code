import { describe, expect, it } from "vitest";

import type { Schema } from "@/api/types";

import { launchPhase, launchProgress, shouldPoll, stageStates } from "./launch";

type Apply = Schema<"ApplyChangesView">;
type Code = Schema<"ApplyAttentionCode">;

function apply(stage: Apply["stage"], extra: Partial<Apply> = {}): Apply {
  return { business_id: "business_1", stage, is_in_progress: stage !== "live", has_unapplied_changes: true, ...extra };
}

function attention(code: Code): Apply {
  return apply("needs_attention", {
    attention: [{ code, message: code, action: { target: "checks", label: "See" } }],
  });
}

describe("launch phase", () => {
  it("is idle before the first launch", () => {
    expect(launchPhase(null)).toBe("idle");
    expect(launchPhase(undefined)).toBe("idle");
    expect(launchPhase(apply(null))).toBe("idle");
    expect(shouldPoll(apply(null))).toBe(false);
  });

  it("runs while building, checking and publishing", () => {
    for (const stage of ["building", "checking", "publishing"] as const) {
      expect(launchPhase(apply(stage))).toBe("running");
      expect(shouldPoll(apply(stage))).toBe(true);
    }
  });

  it("ends live or with reasons", () => {
    expect(launchPhase(apply("live"))).toBe("live");
    expect(launchPhase(attention("checks_failed"))).toBe("attention");
    expect(shouldPoll(apply("live"))).toBe(false);
  });
});

describe("stage states", () => {
  it("move along with the stage", () => {
    expect(stageStates(apply(null))).toEqual({ building: "todo", checking: "todo", publishing: "todo" });
    expect(stageStates(apply("building"))).toEqual({ building: "active", checking: "todo", publishing: "todo" });
    expect(stageStates(apply("checking"))).toEqual({ building: "done", checking: "active", publishing: "todo" });
    expect(stageStates(apply("publishing"))).toEqual({ building: "done", checking: "done", publishing: "active" });
    expect(stageStates(apply("live"))).toEqual({ building: "done", checking: "done", publishing: "done" });
  });

  it("show where a launch stopped", () => {
    expect(stageStates(attention("build_failed"))).toEqual({ building: "stopped", checking: "todo", publishing: "todo" });
    expect(stageStates(attention("profile_incomplete")).building).toBe("stopped");
    expect(stageStates(attention("staff_contact_missing")).building).toBe("stopped");
    expect(stageStates(attention("checks_failed"))).toEqual({ building: "done", checking: "stopped", publishing: "todo" });
    expect(stageStates(attention("checks_stopped")).checking).toBe("stopped");
    expect(stageStates(attention("agreement_not_accepted"))).toEqual({ building: "done", checking: "done", publishing: "stopped" });
    expect(stageStates(attention("payment_needed")).publishing).toBe("stopped");
  });

  it("treat reasons missing from the answer as a stop at publishing", () => {
    expect(stageStates(apply("needs_attention")).publishing).toBe("stopped");
  });
});

describe("launch progress", () => {
  it("grows from building through the checks to live", () => {
    expect(launchProgress(null)).toBe(0);
    expect(launchProgress(apply("building"))).toBeCloseTo(0.08);
    expect(launchProgress(apply("checking", { checks_done: 0, checks_total: 18 }))).toBeCloseTo(0.2);
    expect(launchProgress(apply("checking", { checks_done: 9, checks_total: 18 }))).toBeCloseTo(0.5);
    expect(launchProgress(apply("checking", { checks_done: 30, checks_total: 18 }))).toBeCloseTo(0.8);
    expect(launchProgress(apply("checking"))).toBeCloseTo(0.2);
    expect(launchProgress(apply("publishing"))).toBeCloseTo(0.9);
    expect(launchProgress(apply("live"))).toBe(1);
    expect(launchProgress(attention("checks_failed"))).toBe(0);
  });
});
