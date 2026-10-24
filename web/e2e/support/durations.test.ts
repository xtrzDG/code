import { describe, expect, it } from "vitest";

import { formatDurations, mergeDurations, secondsBySpec } from "../../scripts/e2e-durations.mjs";

/** The shape of Playwright's JSON report, as far as the durations read it. */
const REPORT = {
  stats: { unexpected: 0 },
  suites: [
    {
      title: "inbox.spec.ts",
      file: "inbox.spec.ts",
      specs: [
        {
          title: "the owner answers",
          file: "inbox.spec.ts",
          tests: [{ projectName: "chromium", results: [{ duration: 1500, status: "passed", retry: 0 }] }],
        },
      ],
      suites: [
        {
          title: "on a phone",
          file: "inbox.spec.ts",
          specs: [
            {
              title: "the list fits",
              file: "inbox.spec.ts",
              // A failed attempt and its retry: both ran on the shard.
              tests: [
                {
                  projectName: "chromium",
                  results: [
                    { duration: 2000, status: "failed", retry: 0 },
                    { duration: 1000, status: "passed", retry: 1 },
                  ],
                },
              ],
            },
          ],
        },
      ],
    },
    {
      title: "tour-routes.spec.ts",
      file: "tour-routes.spec.ts",
      specs: [{ title: "the public pages", file: "tour-routes.spec.ts", tests: [{ projectName: "tz-tbilisi", results: [{ duration: 17900 }] }] }],
    },
    { title: "skipped.spec.ts", file: "skipped.spec.ts", specs: [{ title: "later", file: "skipped.spec.ts", tests: [{ results: [] }] }] },
    // Tests a helper module declares (support/axe.ts) count for the spec file that ran them.
    {
      title: "a11y-sections-en.spec.ts",
      file: "a11y-sections-en.spec.ts",
      specs: [{ title: "every section", file: "support/axe.ts", tests: [{ projectName: "chromium", results: [{ duration: 30000 }] }] }],
    },
  ],
};

describe("secondsBySpec", () => {
  it("adds every test, nested group, project and attempt of the spec file that ran it", () => {
    expect(secondsBySpec(REPORT)).toEqual({
      "inbox.spec.ts": 4.5,
      "tour-routes.spec.ts": 17.9,
      "skipped.spec.ts": 0,
      "a11y-sections-en.spec.ts": 30,
    });
  });

  it("reads an empty report as nothing measured", () => {
    expect(secondsBySpec({ suites: [] })).toEqual({});
    expect(secondsBySpec({})).toEqual({});
  });
});

describe("mergeDurations", () => {
  it("replaces the measured specs, keeps the others and drops the specs that are gone", () => {
    const merged = mergeDurations(
      { "inbox.spec.ts": 30, "auth.spec.ts": 6, "gone.spec.ts": 12 },
      { "inbox.spec.ts": 4.5, "new.spec.ts": 2 },
      ["new.spec.ts", "inbox.spec.ts", "auth.spec.ts", "unmeasured.spec.ts"],
    );

    expect(merged).toEqual({ "auth.spec.ts": 6, "inbox.spec.ts": 4.5, "new.spec.ts": 2 });
    expect(Object.keys(merged)).toEqual(["auth.spec.ts", "inbox.spec.ts", "new.spec.ts"]);
  });
});

describe("formatDurations", () => {
  it("writes the names sorted with tenths of a second, one per line", () => {
    expect(formatDurations({ "b.spec.ts": 12.345, "a.spec.ts": 0.04 })).toBe('{\n  "a.spec.ts": 0,\n  "b.spec.ts": 12.3\n}\n');
  });
});
