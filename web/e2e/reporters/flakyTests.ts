/**
 * Tests that passed only on a retry ("flaky"), and which of them are new.
 *
 * The reporter (flakyReporter.ts) writes them to e2e/flaky.json and the job
 * summary. A flaky test that e2e/flaky-known.json does not list is new; on
 * main a new one fails the run, so a flake gets an issue (and an entry in
 * the known list) or a fix, never silence.
 */

export type FlakyTest = {
  /** Spec file inside e2e/, e.g. "inbox.spec.ts". */
  file: string;
  /** Describe titles and the test title, joined with " › ". */
  title: string;
  /** Playwright project ("chromium", "tz-tbilisi"). */
  project: string;
  /** How many runs it took to pass. */
  attempts: number;
};

export type KnownFlakyTest = {
  file: string;
  title: string;
  /** Where the flake is tracked. */
  issue: string;
};

export const MAIN_BRANCH_REF = "refs/heads/main";

/** Parses e2e/flaky-known.json; a malformed list is an error, not "nothing known". */
export function parseKnownFlakyTests(text: string): KnownFlakyTest[] {
  const value: unknown = JSON.parse(text);
  if (!Array.isArray(value)) {
    throw new Error("flaky-known.json must hold a JSON array.");
  }
  return value.map((entry: unknown, index) => {
    const item = (entry ?? {}) as Record<string, unknown>;
    const { file, title, issue } = item;
    if (typeof file !== "string" || typeof title !== "string" || typeof issue !== "string" || !file || !title || !issue) {
      throw new Error(`flaky-known.json entry ${index} needs non-empty "file", "title" and "issue".`);
    }
    return { file, title, issue };
  });
}

function keyOf(test: { file: string; title: string }): string {
  return `${test.file} › ${test.title}`;
}

/** The flaky tests the known list does not name (any project). */
export function newFlakyTests(flaky: readonly FlakyTest[], known: readonly KnownFlakyTest[]): FlakyTest[] {
  const knownKeys = new Set(known.map(keyOf));
  return flaky.filter((test) => !knownKeys.has(keyOf(test)));
}

/** Sorted by file, then title, then project, so reports compare across runs. */
export function sortFlakyTests(flaky: readonly FlakyTest[]): FlakyTest[] {
  return [...flaky].sort(
    (a, b) => a.file.localeCompare(b.file) || a.title.localeCompare(b.title) || a.project.localeCompare(b.project),
  );
}

/** A new flaky test fails the run on main only; pull requests just report it. */
export function failsRun(newOnes: readonly FlakyTest[], ref: string | undefined): boolean {
  return newOnes.length > 0 && ref === MAIN_BRANCH_REF;
}

function cell(text: string): string {
  return text.replace(/\|/g, "\\|").replace(/\r?\n/g, " ");
}

/** The job summary section; empty when nothing was flaky. */
export function flakySummary(flaky: readonly FlakyTest[], newOnes: readonly FlakyTest[], failing: boolean): string {
  if (flaky.length === 0) {
    return "";
  }
  const fresh = new Set(newOnes);
  const lines = [
    `### Flaky end-to-end tests (${flaky.length})`,
    "",
    "Passed only on a retry. New ones belong in an issue and in `web/e2e/flaky-known.json`, or get fixed.",
    "",
    "| Test | Project | Runs | Known |",
    "| --- | --- | --- | --- |",
    ...flaky.map(
      (test) =>
        `| ${cell(test.file)} › ${cell(test.title)} | ${cell(test.project)} | ${test.attempts} | ${fresh.has(test) ? "**new**" : "yes"} |`,
    ),
  ];
  if (failing) {
    lines.push("", `**${newOnes.length} new flaky test(s) on main fail this run.**`);
  }
  return `${lines.join("\n")}\n`;
}
