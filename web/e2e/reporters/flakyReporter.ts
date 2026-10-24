/**
 * A Playwright reporter for tests that passed only on a retry.
 *
 * Writes them to `outputFile` (e2e/flaky.json, an empty list when none; CI
 * keeps it per shard) and to the GitHub job summary, and fails the run on
 * main when one is not in `knownFile` (e2e/flaky-known.json); rules in
 * flakyTests.ts.
 */

import { appendFileSync, readFileSync, writeFileSync } from "node:fs";

import type { FullConfig, FullResult, Reporter, Suite, TestCase } from "@playwright/test/reporter";

import {
  failsRun,
  flakySummary,
  newFlakyTests,
  parseKnownFlakyTests,
  sortFlakyTests,
  type FlakyTest,
} from "./flakyTests";

export type FlakyReporterOptions = {
  /** Where the run's flaky tests go (JSON). */
  outputFile: string;
  /** The flaky tests already tracked in issues (JSON). */
  knownFile: string;
};

type ReportedTest = Pick<TestCase, "outcome" | "titlePath" | "results">;

export function flakyTestsOf(tests: Iterable<ReportedTest>): FlakyTest[] {
  const flaky: FlakyTest[] = [];
  for (const test of tests) {
    if (test.outcome() !== "flaky") {
      continue;
    }
    // ["", project, file, ...describe titles, title]
    const [, project = "", file = "", ...titles] = test.titlePath();
    flaky.push({ file, title: titles.join(" › "), project, attempts: test.results.length });
  }
  return sortFlakyTests(flaky);
}

export default class FlakyReporter implements Reporter {
  private suite: Suite | null = null;

  constructor(private readonly options: FlakyReporterOptions) {}

  onBegin(_config: FullConfig, suite: Suite): void {
    this.suite = suite;
  }

  async onEnd(result: FullResult): Promise<{ status: FullResult["status"] } | undefined> {
    const flaky = flakyTestsOf(this.suite?.allTests() ?? []);
    const known = parseKnownFlakyTests(readFileSync(this.options.knownFile, "utf8"));
    const newOnes = newFlakyTests(flaky, known);
    const failing = failsRun(newOnes, process.env.GITHUB_REF);

    writeFileSync(this.options.outputFile, `${JSON.stringify(flaky, null, 2)}\n`);
    const summary = flakySummary(flaky, newOnes, failing);
    const summaryPath = process.env.GITHUB_STEP_SUMMARY;
    if (summary && summaryPath) {
      appendFileSync(summaryPath, summary);
    }
    for (const test of flaky) {
      const label = newOnes.includes(test) ? "new flaky" : "known flaky";
      console.warn(`${label}: ${test.file} › ${test.title} [${test.project}], passed on run ${test.attempts}`);
    }
    return failing && result.status === "passed" ? { status: "failed" } : undefined;
  }

  printsToStdio(): boolean {
    return false;
  }
}
