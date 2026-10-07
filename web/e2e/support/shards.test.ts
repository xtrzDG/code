import { mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";

import { describe, expect, it } from "vitest";

import {
  matchSpecs,
  parseShard,
  planShards,
  readDurations,
  readSpecNames,
  specsOfShard,
  weighSpecs,
  type WeighedSpec,
} from "./shards";

const E2E_DIRECTORY = path.resolve(__dirname, "..");
const DURATIONS_PATH = path.join(E2E_DIRECTORY, "durations.json");
const CI_WORKFLOW = path.resolve(E2E_DIRECTORY, "..", "..", ".github", "workflows", "ci.yml");
/**
 * The most measured seconds of specs one CI shard may run. CI's machines
 * ran this suite about 1.1 times slower than a developer's (run 37537772194
 * against a local run of the same commit), and every shard also starts the
 * API and the cabinet: 190 local seconds come to about four minutes there.
 */
const SHARD_BUDGET_SECONDS = 190;

function spec(name: string, seconds: number, measured = true): WeighedSpec {
  return { name, seconds, measured };
}

describe("parseShard", () => {
  it("reads index/total and runs everything without a value", () => {
    expect(parseShard("2/8")).toEqual({ index: 2, total: 8 });
    expect(parseShard(" 1/1 ")).toEqual({ index: 1, total: 1 });
    expect(parseShard(undefined)).toBeNull();
    expect(parseShard("")).toBeNull();
  });

  it.each(["0/4", "5/4", "1/0", "two/4", "1-4", "1/4/2"])("refuses %s", (value) => {
    expect(() => parseShard(value)).toThrow(/E2E_SHARD/);
  });
});

describe("weighSpecs", () => {
  it("weighs a measured spec by its seconds and the others by the mean of the measured ones", () => {
    const weighed = weighSpecs(["a.spec.ts", "b.spec.ts", "new.spec.ts"], { "a.spec.ts": 10, "b.spec.ts": 30, "gone.spec.ts": 500 });

    expect(weighed).toEqual([spec("a.spec.ts", 10), spec("b.spec.ts", 30), spec("new.spec.ts", 20, false)]);
  });

  it("weighs every spec the same while nothing is measured", () => {
    expect(weighSpecs(["a.spec.ts", "b.spec.ts"], {})).toEqual([spec("a.spec.ts", 1, false), spec("b.spec.ts", 1, false)]);
  });
});

describe("planShards", () => {
  it("gives the longest spec first to the shard with the least work", () => {
    const plan = planShards([spec("a.spec.ts", 5), spec("b.spec.ts", 9), spec("c.spec.ts", 4), spec("d.spec.ts", 3), spec("e.spec.ts", 2)], 2);

    // b → 1 (9); a → 2 (5); c → 2 (9); d → 1 (12); e → 2 (11).
    expect(plan).toEqual([
      { names: ["b.spec.ts", "d.spec.ts"], seconds: 12 },
      { names: ["a.spec.ts", "c.spec.ts", "e.spec.ts"], seconds: 11 },
    ]);
  });

  it("gives every spec to exactly one shard, none of them heavier than the lightest plus the longest spec", () => {
    const specs = Array.from({ length: 40 }, (_, index) => spec(`s${String(index).padStart(2, "0")}.spec.ts`, ((index * 37) % 23) + 1));
    const plan = planShards(specs, 6);

    expect(plan.flatMap((shard) => shard.names).sort()).toEqual(specs.map((item) => item.name));
    const loads = plan.map((shard) => shard.seconds);
    expect(Math.max(...loads) - Math.min(...loads)).toBeLessThanOrEqual(23);
  });

  it("does not depend on the order the files were read in, and breaks ties by name", () => {
    const specs = [spec("a.spec.ts", 3), spec("b.spec.ts", 3), spec("c.spec.ts", 2), spec("d.spec.ts", 1)];

    expect(planShards([...specs].reverse(), 2)).toEqual(planShards(specs, 2));
    // a and b weigh the same: a goes first, so c joins a's shard and d b's.
    expect(planShards(specs, 2).map((shard) => shard.names)).toEqual([
      ["a.spec.ts", "c.spec.ts"],
      ["b.spec.ts", "d.spec.ts"],
    ]);
  });

  it("leaves a shard empty when there are fewer specs than shards", () => {
    expect(planShards([spec("a.spec.ts", 3)], 2)).toEqual([
      { names: ["a.spec.ts"], seconds: 3 },
      { names: [], seconds: 0 },
    ]);
  });
});

describe("readDurations", () => {
  it("refuses a file that is not a map of seconds", () => {
    const directory = mkdtempSync(path.join(tmpdir(), "e2e-durations-"));
    let files = 0;
    const write = (text: string) => {
      files += 1;
      const file = path.join(directory, `durations-${files}.json`);
      writeFileSync(file, text);
      return file;
    };

    expect(() => readDurations(write("[1, 2]"))).toThrow(/map spec file names to seconds/);
    expect(() => readDurations(write('{"a.spec.ts": "slow"}'))).toThrow(/"a.spec.ts" must be a number of seconds/);
    expect(() => readDurations(write('{"a.spec.ts": -1}'))).toThrow(/must be a number of seconds/);
    expect(readDurations(write('{"a.spec.ts": 12.5}'))).toEqual({ "a.spec.ts": 12.5 });
    expect(readDurations(path.join(directory, "missing.json"))).toEqual({});
  });
});

describe("the suite's own specs", () => {
  const names = readSpecNames(E2E_DIRECTORY);
  const durations = readDurations(DURATIONS_PATH);
  const suite = weighSpecs(names, durations);
  const workflow = readFileSync(CI_WORKFLOW, "utf8");
  const shardTotal = Number(/E2E_SHARD: \$\{\{ matrix\.shard \}\}\/(\d+)/.exec(workflow)?.[1]);

  it("all have a measured duration, and every duration a spec (npm run e2e:durations)", () => {
    const unmeasured = names.filter((name) => !Object.hasOwn(durations, name));
    const gone = Object.keys(durations).filter((name) => !names.includes(name));

    expect(unmeasured, "measure them: npm run e2e:durations -- <files> (web/README.md)").toEqual([]);
    expect(gone, "spec files that no longer exist (any npm run e2e:durations drops them)").toEqual([]);
  });

  it("split into CI's shards, which together run every spec once", () => {
    const matrix = /shard: \[([\d, ]+)\]/.exec(workflow)?.[1]?.split(",").map(Number);
    const shards = Array.from({ length: shardTotal }, (_, index) => specsOfShard(suite, { index: index + 1, total: shardTotal }));

    expect(shardTotal).toBeGreaterThan(1);
    expect(matrix).toEqual(Array.from({ length: shardTotal }, (_, index) => index + 1));
    expect(shards.flat().sort()).toEqual(names);
    expect(shards.every((shard) => shard.length > 0)).toBe(true);
  });

  it(`keep every CI shard within ${SHARD_BUDGET_SECONDS} measured seconds (split a long spec or add a shard)`, () => {
    const overBudget = planShards(suite, shardTotal)
      .map((shard, index) => ({ shard: index + 1, seconds: Math.round(shard.seconds), specs: shard.names }))
      .filter((shard) => shard.seconds > SHARD_BUDGET_SECONDS);

    expect(overBudget).toEqual([]);
  });

  it("include the route tour, which runs in Tbilisi (playwright.config.ts)", () => {
    expect(names.filter((name) => name.startsWith("tour-"))).toEqual([
      "tour-routes-business.spec.ts",
      "tour-routes-settings.spec.ts",
      "tour-routes.spec.ts",
    ]);
  });
});

describe("matchSpecs", () => {
  it("matches exactly the named files, never a longer name", () => {
    const pattern = matchSpecs(["inbox.spec.ts", "a11y.spec.ts"]);

    expect(pattern.test("/repo/web/e2e/inbox.spec.ts")).toBe(true);
    expect(pattern.test("C:\\repo\\web\\e2e\\a11y.spec.ts")).toBe(true);
    expect(pattern.test("/repo/web/e2e/public-a11y.spec.ts")).toBe(false);
    expect(pattern.test("/repo/web/e2e/inboxXspec.ts")).toBe(false);
    expect(matchSpecs([]).test("/repo/web/e2e/inbox.spec.ts")).toBe(false);
  });
});
