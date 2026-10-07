#!/usr/bin/env node
/**
 * e2e/durations.json: the seconds each end-to-end spec file took, which CI
 * balances its shards by (e2e/support/shards.ts). Measured with Playwright's
 * JSON reporter:
 *
 *   npm run e2e:durations                          # the whole suite (about 25 minutes)
 *   npm run e2e:durations -- inbox.spec.ts         # these files; the rest keep their entries
 *   npm run e2e:durations -- --from report.json …  # JSON reports of a CI run
 *
 * The last form reads the `report.json` of each `e2e-report-<shard>`
 * artifact: durations measured on CI's own machines. A spec file the
 * reports measured replaces its entry, entries of spec files that no longer
 * exist are dropped, every other entry stays. A run with a failed test
 * writes nothing: a failure's duration is its timeout, not the spec's.
 */

import { spawnSync } from "node:child_process";
import { readdirSync, readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const WEB_DIRECTORY = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const E2E_DIRECTORY = path.join(WEB_DIRECTORY, "e2e");
const DURATIONS_PATH = path.join(E2E_DIRECTORY, "durations.json");
const REPORT_PATH = path.join(E2E_DIRECTORY, ".artifacts", "durations-report.json");
const SPEC_SUFFIX = ".spec.ts";

/** Seconds per spec file of a Playwright JSON report: every test, project and attempt. */
export function secondsBySpec(report) {
  const totals = new Map();
  const visit = (suite, file) => {
    const suiteFile = suite.file ?? file;
    for (const spec of suite.specs ?? []) {
      const name = path.basename(spec.file ?? suiteFile);
      const milliseconds = (spec.tests ?? [])
        .flatMap((test) => test.results ?? [])
        .reduce((sum, result) => sum + (result.duration ?? 0), 0);
      totals.set(name, (totals.get(name) ?? 0) + milliseconds);
    }
    for (const child of suite.suites ?? []) {
      visit(child, suiteFile);
    }
  };
  for (const suite of report.suites ?? []) {
    visit(suite, suite.file);
  }
  return Object.fromEntries([...totals].map(([name, milliseconds]) => [name, milliseconds / 1000]));
}

/** The new entries: measured specs replace theirs, specs that are gone are dropped. */
export function mergeDurations(previous, measured, specNames) {
  const merged = {};
  for (const name of [...specNames].sort()) {
    if (Object.hasOwn(measured, name)) {
      merged[name] = measured[name];
    } else if (Object.hasOwn(previous, name)) {
      merged[name] = previous[name];
    }
  }
  return merged;
}

/** The file's text: names sorted, tenths of a second, one entry per line. */
export function formatDurations(durations) {
  const rounded = Object.keys(durations)
    .sort()
    .map((name) => [name, Math.round(durations[name] * 10) / 10]);
  return `${JSON.stringify(Object.fromEntries(rounded), null, 2)}\n`;
}

function readJson(file) {
  return JSON.parse(readFileSync(file, "utf8"));
}

function failedTests(report) {
  return (report.stats?.unexpected ?? 0) > 0;
}

/** Runs the suite (or the given files) with the JSON reporter; its report. */
function measure(playwrightArguments) {
  const run = spawnSync(
    "npx",
    ["playwright", "test", "--config", "e2e/playwright.config.ts", "--reporter=list,json", ...playwrightArguments],
    { cwd: WEB_DIRECTORY, stdio: "inherit", env: { ...process.env, PLAYWRIGHT_JSON_OUTPUT_FILE: REPORT_PATH } },
  );
  if (run.status !== 0) {
    console.error("The run failed: e2e/durations.json is left as it was.");
    process.exit(run.status ?? 1);
  }
  return [readJson(REPORT_PATH)];
}

function main(argv) {
  const reports = [];
  const playwrightArguments = [];
  for (let index = 0; index < argv.length; index += 1) {
    if (argv[index] === "--from") {
      reports.push(readJson(argv[index + 1]));
      index += 1;
    } else {
      playwrightArguments.push(argv[index]);
    }
  }
  const measuredReports = reports.length > 0 ? reports : measure(playwrightArguments);
  if (measuredReports.some(failedTests)) {
    console.error("A report has failed tests: e2e/durations.json is left as it was.");
    process.exit(1);
  }
  const measured = Object.assign({}, ...measuredReports.map(secondsBySpec));
  const specNames = readdirSync(E2E_DIRECTORY).filter((name) => name.endsWith(SPEC_SUFFIX));
  let previous = {};
  try {
    previous = readJson(DURATIONS_PATH);
  } catch {
    // No durations yet: every entry comes from this measurement.
  }
  writeFileSync(DURATIONS_PATH, formatDurations(mergeDurations(previous, measured, specNames)));
  console.log(`e2e/durations.json: ${Object.keys(measured).length} spec files measured.`);
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  main(process.argv.slice(2));
}
