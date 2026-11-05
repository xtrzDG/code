import { describe, expect, it } from "vitest";

import {
  failsRun,
  flakySummary,
  MAIN_BRANCH_REF,
  newFlakyTests,
  parseKnownFlakyTests,
  sortFlakyTests,
  type FlakyTest,
} from "./flakyTests";

function flaky(file: string, title: string, project = "chromium"): FlakyTest {
  return { file, title, project, attempts: 2 };
}

const ISSUE = "https://github.com/owner/repo/issues/12";

describe("parseKnownFlakyTests", () => {
  it("reads the tracked flakes", () => {
    expect(parseKnownFlakyTests(`[{"file": "a.spec.ts", "title": "t", "issue": "${ISSUE}"}]`)).toEqual([
      { file: "a.spec.ts", title: "t", issue: ISSUE },
    ]);
    expect(parseKnownFlakyTests("[]")).toEqual([]);
  });

  it.each([
    ['{"file": "a.spec.ts"}', /JSON array/],
    ['[{"file": "a.spec.ts", "title": "t"}]', /entry 0 needs/],
    ['[{"file": "", "title": "t", "issue": "i"}]', /entry 0 needs/],
    ["[null]", /entry 0 needs/],
  ])("refuses %s", (text, error) => {
    expect(() => parseKnownFlakyTests(text)).toThrow(error);
  });
});

describe("newFlakyTests", () => {
  it("leaves out the known ones in every project", () => {
    const known = [{ file: "a.spec.ts", title: "t", issue: ISSUE }];
    const run = [flaky("a.spec.ts", "t"), flaky("a.spec.ts", "t", "tz-tbilisi"), flaky("a.spec.ts", "other"), flaky("b.spec.ts", "t")];

    expect(newFlakyTests(run, known)).toEqual([flaky("a.spec.ts", "other"), flaky("b.spec.ts", "t")]);
  });
});

describe("failsRun", () => {
  it("fails only on main and only for new flakes", () => {
    expect(failsRun([flaky("a.spec.ts", "t")], MAIN_BRANCH_REF)).toBe(true);
    expect(failsRun([], MAIN_BRANCH_REF)).toBe(false);
    expect(failsRun([flaky("a.spec.ts", "t")], "refs/pull/7/merge")).toBe(false);
    expect(failsRun([flaky("a.spec.ts", "t")], undefined)).toBe(false);
  });
});

describe("sortFlakyTests", () => {
  it("orders by file, title and project", () => {
    const sorted = sortFlakyTests([flaky("b.spec.ts", "a"), flaky("a.spec.ts", "b", "z"), flaky("a.spec.ts", "b", "c"), flaky("a.spec.ts", "a")]);

    expect(sorted.map((test) => `${test.file}/${test.title}/${test.project}`)).toEqual([
      "a.spec.ts/a/chromium",
      "a.spec.ts/b/c",
      "a.spec.ts/b/z",
      "b.spec.ts/a/chromium",
    ]);
  });
});

describe("flakySummary", () => {
  it("is empty without flaky tests", () => {
    expect(flakySummary([], [], false)).toBe("");
  });

  it("tables every flaky test, marks the new ones and keeps the table intact", () => {
    const known = flaky("a.spec.ts", "known");
    const fresh = flaky("b.spec.ts", "pipes | and\nnewlines");

    const summary = flakySummary([known, fresh], [fresh], true);

    expect(summary).toContain("### Flaky end-to-end tests (2)");
    expect(summary).toContain("| a.spec.ts › known | chromium | 2 | yes |");
    expect(summary).toContain("| b.spec.ts › pipes \\| and newlines | chromium | 2 | **new** |");
    expect(summary).toContain("**1 new flaky test(s) on main fail this run.**");
  });
});
