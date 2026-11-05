/**
 * Settings of the property tests (fast-check). Reproducible by default:
 * a fixed seed, so CI runs the same cases every time and a failure
 * reproduces locally. `FC_SEED=random` (or a number) explores new cases;
 * a failure it finds becomes a fixed example of its test.
 */

import type { Parameters } from "fast-check";

const DEFAULT_SEED = 20_261_005;

function seed(): number | undefined {
  const value = process.env.FC_SEED;
  if (value === "random") {
    return undefined;
  }
  return value ? Number(value) : DEFAULT_SEED;
}

export function propertyParameters<T>(numRuns = 300): Parameters<T> {
  const fixedSeed = seed();
  return fixedSeed === undefined ? { numRuns } : { numRuns, seed: fixedSeed };
}
