/**
 * Which spec files a CI shard runs (E2E_SHARD="2/4", playwright.config.ts).
 *
 * Every shard starts its own API (in-memory storage, demo data), so the specs
 * that share state on it stay together: the platform admin specs
 * (support/admin.ts) build one admin team, the run's first admin adding the
 * others and keeping their authenticators in e2e/.artifacts. They form one
 * unit; every other spec is a unit of its own. Units go, heaviest first, to
 * the shard with the least work so far; a unit weighs its number of tests.
 * The plan is a pure function of the files, so every shard computes the
 * same one.
 */

import { readdirSync, readFileSync } from "node:fs";
import path from "node:path";

export type SpecFile = {
  /** File name inside e2e/, e.g. "inbox.spec.ts". */
  name: string;
  /** Its number of tests (at least 1). */
  weight: number;
  /** It signs in through support/admin.ts and shares the admin team. */
  sharesAdminState: boolean;
};

export type Shard = { index: number; total: number };

const SPEC_SUFFIX = ".spec.ts";
const TEST_CALL = /^\s*test(?:\.(?:only|skip|fixme|fail))?\(/gm;
const ADMIN_IMPORT = /from\s+["']\.\/support\/admin["']/;
const SHARD_PATTERN = /^(\d+)\/(\d+)$/;

/** "2/4" → { index: 2, total: 4 }; nothing → every spec (local runs). */
export function parseShard(value: string | undefined): Shard | null {
  if (!value) {
    return null;
  }
  const match = SHARD_PATTERN.exec(value.trim());
  const index = Number(match?.[1]);
  const total = Number(match?.[2]);
  if (!match || total < 1 || index < 1 || index > total) {
    throw new Error(`E2E_SHARD must look like "2/4" (shard 1..total), not "${value}".`);
  }
  return { index, total };
}

export function describeSpec(name: string, source: string): SpecFile {
  return {
    name,
    weight: Math.max(1, source.match(TEST_CALL)?.length ?? 0),
    sharesAdminState: ADMIN_IMPORT.test(source),
  };
}

export function readSpecFiles(directory: string): SpecFile[] {
  return readdirSync(directory)
    .filter((name) => name.endsWith(SPEC_SUFFIX))
    .sort()
    .map((name) => describeSpec(name, readFileSync(path.join(directory, name), "utf8")));
}

type Unit = { names: string[]; weight: number };

function unitsOf(files: readonly SpecFile[]): Unit[] {
  const specs = [...files].sort((a, b) => a.name.localeCompare(b.name));
  const admin = specs.filter((spec) => spec.sharesAdminState);
  const units: Unit[] = specs
    .filter((spec) => !spec.sharesAdminState)
    .map((spec) => ({ names: [spec.name], weight: spec.weight }));
  if (admin.length > 0) {
    units.push({ names: admin.map((spec) => spec.name), weight: admin.reduce((sum, spec) => sum + spec.weight, 0) });
  }
  return units.sort((a, b) => b.weight - a.weight || a.names[0]!.localeCompare(b.names[0]!));
}

/** The spec file names of every shard, in shard order; each list sorted. */
export function planShards(specs: readonly SpecFile[], total: number): string[][] {
  const shards = Array.from({ length: total }, () => ({ names: [] as string[], weight: 0 }));
  for (const unit of unitsOf(specs)) {
    const lightest = shards.reduce((best, shard) => (shard.weight < best.weight ? shard : best));
    lightest.names.push(...unit.names);
    lightest.weight += unit.weight;
  }
  return shards.map((shard) => shard.names.sort());
}

/** The spec file names the given shard runs. */
export function specsOfShard(specs: readonly SpecFile[], shard: Shard): string[] {
  return planShards(specs, shard.total)[shard.index - 1] ?? [];
}

/** A testMatch pattern for exactly these spec files. */
export function matchSpecs(names: readonly string[]): RegExp {
  const escaped = names.map((name) => name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
  return new RegExp(`(?:^|[\\\\/])(?:${escaped.join("|") || "(?!)"})$`);
}
