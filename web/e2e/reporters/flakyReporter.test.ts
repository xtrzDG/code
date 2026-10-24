import { mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";

import type { FullConfig, Suite, TestCase } from "@playwright/test/reporter";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import FlakyReporter, { flakyTestsOf } from "./flakyReporter";
import { MAIN_BRANCH_REF } from "./flakyTests";

type Outcome = ReturnType<TestCase["outcome"]>;

function reported(outcome: Outcome, titlePath: string[], runs: number): TestCase {
  return {
    outcome: () => outcome,
    titlePath: () => titlePath,
    results: Array.from({ length: runs }, () => ({})),
  } as unknown as TestCase;
}

const FLAKY_INBOX = reported("flaky", ["", "chromium", "inbox.spec.ts", "Inbox", "assigns a conversation"], 2);
const FLAKY_TOUR = reported("flaky", ["", "tz-tbilisi", "tour-routes.spec.ts", "admin routes"], 2);
const PASSED = reported("expected", ["", "chromium", "auth.spec.ts", "signs in"], 1);
const FAILED = reported("unexpected", ["", "chromium", "auth.spec.ts", "signs out"], 2);

function suiteOf(tests: TestCase[]): Suite {
  return { allTests: () => tests } as unknown as Suite;
}

describe("flakyTestsOf", () => {
  it("keeps the tests that passed on a retry, with their describe chain", () => {
    expect(flakyTestsOf([PASSED, FLAKY_TOUR, FAILED, FLAKY_INBOX])).toEqual([
      { file: "inbox.spec.ts", title: "Inbox › assigns a conversation", project: "chromium", attempts: 2 },
      { file: "tour-routes.spec.ts", title: "admin routes", project: "tz-tbilisi", attempts: 2 },
    ]);
  });
});

describe("FlakyReporter", () => {
  let directory: string;
  let outputFile: string;
  let knownFile: string;
  let summaryFile: string;

  beforeEach(() => {
    directory = mkdtempSync(path.join(tmpdir(), "flaky-"));
    outputFile = path.join(directory, "flaky.json");
    knownFile = path.join(directory, "flaky-known.json");
    summaryFile = path.join(directory, "summary.md");
    writeFileSync(knownFile, "[]\n");
    writeFileSync(summaryFile, "");
    vi.stubEnv("GITHUB_STEP_SUMMARY", summaryFile);
    vi.spyOn(console, "warn").mockImplementation(() => undefined);
  });

  afterEach(() => {
    vi.unstubAllEnvs();
  });

  function run(tests: TestCase[], status: "passed" | "failed" = "passed") {
    const reporter = new FlakyReporter({ outputFile, knownFile });
    reporter.onBegin({} as FullConfig, suiteOf(tests));
    return reporter.onEnd({ status, startTime: new Date(0), duration: 1 });
  }

  it("writes an empty list and no summary when nothing was flaky", async () => {
    vi.stubEnv("GITHUB_REF", MAIN_BRANCH_REF);

    await expect(run([PASSED])).resolves.toBeUndefined();
    expect(JSON.parse(readFileSync(outputFile, "utf8"))).toEqual([]);
    expect(readFileSync(summaryFile, "utf8")).toBe("");
  });

  it("reports a new flaky test on a pull request without failing it", async () => {
    vi.stubEnv("GITHUB_REF", "refs/pull/42/merge");

    await expect(run([FLAKY_INBOX, PASSED])).resolves.toBeUndefined();
    expect(JSON.parse(readFileSync(outputFile, "utf8"))).toHaveLength(1);
    const summary = readFileSync(summaryFile, "utf8");
    expect(summary).toContain("inbox.spec.ts › Inbox › assigns a conversation | chromium | 2 | **new**");
    expect(summary).not.toContain("fail this run");
  });

  it("fails a passing run on main for a new flaky test", async () => {
    vi.stubEnv("GITHUB_REF", MAIN_BRANCH_REF);

    await expect(run([FLAKY_INBOX])).resolves.toEqual({ status: "failed" });
    expect(readFileSync(summaryFile, "utf8")).toContain("1 new flaky test(s) on main fail this run");
  });

  it("lets a known flaky test pass on main", async () => {
    vi.stubEnv("GITHUB_REF", MAIN_BRANCH_REF);
    writeFileSync(
      knownFile,
      JSON.stringify([{ file: "inbox.spec.ts", title: "Inbox › assigns a conversation", issue: "https://github.com/o/r/issues/7" }]),
    );

    await expect(run([FLAKY_INBOX])).resolves.toBeUndefined();
    expect(readFileSync(summaryFile, "utf8")).toContain("| chromium | 2 | yes |");
  });

  it("leaves a failed run failed and still writes its flaky tests", async () => {
    vi.stubEnv("GITHUB_REF", MAIN_BRANCH_REF);

    await expect(run([FLAKY_TOUR, FAILED], "failed")).resolves.toBeUndefined();
    expect(JSON.parse(readFileSync(outputFile, "utf8"))).toEqual([
      { file: "tour-routes.spec.ts", title: "admin routes", project: "tz-tbilisi", attempts: 2 },
    ]);
  });

  it("refuses a malformed known list", async () => {
    writeFileSync(knownFile, JSON.stringify([{ file: "inbox.spec.ts" }]));

    await expect(run([FLAKY_INBOX])).rejects.toThrow(/entry 0 needs/);
  });
});
