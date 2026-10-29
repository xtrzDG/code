import { describe, expect, it } from "vitest";

import { answeredTarget, chatChoices, initialTarget, storedTarget } from "./chatTargets";
import type { AssistantVersionStatus } from "./versions";

function version(id: string, number: number, status: AssistantVersionStatus) {
  return { id, version_number: number, status };
}

const live = version("v2", 2, "published");
const draft = version("v3", 3, "tests_failed");
const old = version("v1", 1, "archived");
const versions = [old, live, draft];

describe("who the test chat talks to", () => {
  it("offers what customers get now and the owner's changes, never version numbers", () => {
    expect(chatChoices(versions, null)).toEqual([
      { target: "live", versionId: "v2", versionNumber: null },
      { target: "changes", versionId: null, versionNumber: null },
    ]);
  });

  it("offers only the owner's changes before anything is live", () => {
    expect(chatChoices([version("v1", 1, "ready")], null).map((choice) => choice.target)).toEqual(["changes"]);
  });

  it("adds an update from History only when the page was opened for it", () => {
    expect(chatChoices(versions, "v1").at(-1)).toEqual({ target: "history", versionId: "v1", versionNumber: 1 });
    // The live version opened from History is simply "What customers get now".
    expect(chatChoices(versions, "v2")).toHaveLength(2);
    expect(chatChoices(versions, "gone")).toHaveLength(2);
  });

  it("starts from the page's version, else with the owner's changes", () => {
    expect(initialTarget(versions, "v2")).toBe("live");
    expect(initialTarget(versions, "v1")).toBe("history");
    expect(initialTarget(versions, "gone")).toBe("changes");
    expect(initialTarget(versions, null)).toBe("changes");
  });

  it("reads conversations kept before targets were stored", () => {
    expect(storedTarget(versions, { versionId: "v2" })).toBe("live");
    expect(storedTarget(versions, { versionId: "v3" })).toBe("changes");
    expect(storedTarget(versions, { versionId: null })).toBe("changes");
    expect(storedTarget(versions, { versionId: "v1", target: "history" })).toBe("history");
  });

  it("names which choice answered a line", () => {
    expect(answeredTarget(versions, "v2", null)).toBe("live");
    expect(answeredTarget(versions, "v1", "v1")).toBe("history");
    expect(answeredTarget(versions, "v3", null)).toBe("changes");
    expect(answeredTarget(versions, null, null)).toBe("changes");
  });
});
