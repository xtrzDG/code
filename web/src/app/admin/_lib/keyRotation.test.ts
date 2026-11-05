import { describe, expect, it } from "vitest";

import { findingTone, isRotationRunning, rotationFindings, type KeyRotation } from "./keyRotation";

function run(overrides: Partial<KeyRotation> = {}): KeyRotation {
  return {
    id: "key_rotation_1",
    status: "done",
    key_count: 2,
    secrets_total: 5,
    secrets_current: 1,
    secrets_rotated: 4,
    secrets_unreadable: 0,
    webhooks_renewed: 2,
    webhooks_failed: 0,
    requested_at: 1_700_000_000_000_000,
    started_at: 1_700_000_001_000_000,
    finished_at: 1_700_000_002_000_000,
    last_error: null,
    ...overrides,
  };
}

describe("isRotationRunning", () => {
  it("is true while the worker has not finished", () => {
    expect(isRotationRunning(run({ status: "queued" }))).toBe(true);
    expect(isRotationRunning(run({ status: "running" }))).toBe(true);
    expect(isRotationRunning(run({ status: "done" }))).toBe(false);
    expect(isRotationRunning(run({ status: "failed" }))).toBe(false);
    expect(isRotationRunning(null)).toBe(false);
    expect(isRotationRunning(undefined)).toBe(false);
  });
});

describe("rotationFindings", () => {
  it("says a run is working and nothing else while it runs", () => {
    expect(rotationFindings(run({ status: "running", secrets_unreadable: 3 }), 2)).toEqual([{ kind: "working" }]);
  });

  it("names the error of a failed run", () => {
    expect(rotationFindings(run({ status: "failed", last_error: "RuntimeError: database went away" }), 2)).toEqual([
      { kind: "failed", error: "RuntimeError: database went away" },
    ]);
    expect(rotationFindings(run({ status: "failed", last_error: null }), 2)).toEqual([{ kind: "failed", error: "" }]);
  });

  it("is clean when every token opened and every webhook was registered again", () => {
    expect(rotationFindings(run(), 2)).toEqual([{ kind: "clean", isSingleKey: false }]);
    expect(rotationFindings(run({ key_count: 1 }), 1)).toEqual([{ kind: "clean", isSingleKey: true }]);
  });

  it("stays clean after the old keys were removed", () => {
    expect(rotationFindings(run({ key_count: 2 }), 1)).toEqual([{ kind: "clean", isSingleKey: true }]);
  });

  it("lists unreadable tokens, failed webhooks and a key added since, most urgent first", () => {
    expect(rotationFindings(run({ secrets_unreadable: 2, webhooks_failed: 1, key_count: 2 }), 3)).toEqual([
      { kind: "unreadable", count: 2 },
      { kind: "webhooks", count: 1 },
      { kind: "keysChanged", then: 2, now: 3 },
    ]);
  });
});

describe("findingTone", () => {
  it("colours each finding", () => {
    expect(findingTone({ kind: "working" })).toBe("info");
    expect(findingTone({ kind: "clean", isSingleKey: false })).toBe("success");
    expect(findingTone({ kind: "failed", error: "x" })).toBe("danger");
    expect(findingTone({ kind: "unreadable", count: 1 })).toBe("warning");
    expect(findingTone({ kind: "webhooks", count: 1 })).toBe("warning");
    expect(findingTone({ kind: "keysChanged", then: 1, now: 2 })).toBe("warning");
  });
});
