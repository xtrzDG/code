/**
 * Which spec files a CI shard runs (E2E_SHARD="2/8", playwright.config.ts).
 *
 * Every shard starts its own API (in-memory storage, demo data) and every
 * spec builds what it needs on it: an owner signs up, a platform admin is
 * added to the team by the run's first admin (support/admin.ts). So any spec
 * may run on any shard, and the plan balances the shards by time: a spec
 * weighs the seconds it took in the last measured run (e2e/durations.json),
 * a spec not measured yet the mean of the measured ones; specs go, longest
 * first, to the shard with the least work so far. The plan is a pure
 * function of the spec names and the durations, so every shard computes the
 * same one.
 *
 * `npm run e2e:durations` measures the suite again (scripts/e2e-durations.mjs,
 * web/README.md "End-to-end tests"); support/shards.test.ts fails while a
 * spec has no measurement or a shard of CI's plan runs over its budget.
 */

import { existsSync, readdirSync, readFileSync } from "node:fs";

export type Shard = { index: number; total: number };

/** Seconds each spec file took in the last measured run, by file name. */
export type SpecDurations = Readonly<Record<string, number>>;

export type WeighedSpec = {
  /** File name inside e2e/, e.g. "inbox.spec.ts". */
  name: string;
  /** Its measured seconds, or the mean of the measured specs. */
  seconds: number;
  measured: boolean;
};

export type PlannedShard = { names: string[]; seconds: number };

const SPEC_SUFFIX = ".spec.ts";
const SHARD_PATTERN = /^(\d+)\/(\d+)$/;
/** The weight of every spec while nothing is measured at all. */
const UNMEASURED_SECONDS = 1;

/** "2/8" → { index: 2, total: 8 }; nothing → every spec (local runs). */
export function parseShard(value: string | undefined): Shard | null {
  if (!value) {
    return null;
  }
  const match = SHARD_PATTERN.exec(value.trim());
  const index = Number(match?.[1]);
  const total = Number(match?.[2]);
  if (!match || total < 1 || index < 1 || index > total) {
    throw new Error(`E2E_SHARD must look like "2/8" (shard 1..total), not "${value}".`);
  }
  return { index, total };
}

/** The spec files of the suite, sorted. */
export function readSpecNames(directory: string): string[] {
  return readdirSync(directory)
    .filter((name) => name.endsWith(SPEC_SUFFIX))
    .sort();
}

/** e2e/durations.json; nothing measured when the file is missing. */
export function readDurations(file: string): SpecDurations {
  if (!existsSync(file)) {
    return {};
  }
  const parsed: unknown = JSON.parse(readFileSync(file, "utf8"));
  if (parsed === null || typeof parsed !== "object" || Array.isArray(parsed)) {
    throw new Error(`${file} must map spec file names to seconds.`);
  }
  for (const [name, seconds] of Object.entries(parsed)) {
    if (typeof seconds !== "number" || !Number.isFinite(seconds) || seconds < 0) {
      throw new Error(`${file}: "${name}" must be a number of seconds, not ${JSON.stringify(seconds)}.`);
    }
  }
  return parsed as SpecDurations;
}

/** Each spec with its weight: its measurement, or the mean of the measured specs. */
export function weighSpecs(names: readonly string[], durations: SpecDurations): WeighedSpec[] {
  const measured = names.filter((name) => Object.hasOwn(durations, name)).map((name) => durations[name]!);
  const mean = measured.length > 0 ? measured.reduce((sum, seconds) => sum + seconds, 0) / measured.length : UNMEASURED_SECONDS;
  return names.map((name) =>
    Object.hasOwn(durations, name)
      ? { name, seconds: durations[name]!, measured: true }
      : { name, seconds: mean, measured: false },
  );
}

/** Every shard's spec names (sorted) and seconds, in shard order. */
export function planShards(specs: readonly WeighedSpec[], total: number): PlannedShard[] {
  const shards: PlannedShard[] = Array.from({ length: total }, () => ({ names: [], seconds: 0 }));
  const longestFirst = [...specs].sort((a, b) => b.seconds - a.seconds || a.name.localeCompare(b.name));
  for (const spec of longestFirst) {
    const lightest = shards.reduce((best, shard) => (shard.seconds < best.seconds ? shard : best));
    lightest.names.push(spec.name);
    lightest.seconds += spec.seconds;
  }
  for (const shard of shards) {
    shard.names.sort();
  }
  return shards;
}

/** The spec file names the given shard runs. */
export function specsOfShard(specs: readonly WeighedSpec[], shard: Shard): string[] {
  return planShards(specs, shard.total)[shard.index - 1]?.names ?? [];
}

/** A testMatch pattern for exactly these spec files. */
export function matchSpecs(names: readonly string[]): RegExp {
  const escaped = names.map((name) => name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
  return new RegExp(`(?:^|[\\\\/])(?:${escaped.join("|") || "(?!)"})$`);
}
