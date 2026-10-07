/** Types of scripts/e2e-durations.mjs for its tests (e2e/support/durations.test.ts). */

export type SpecDurations = Record<string, number>;

export function secondsBySpec(report: unknown): SpecDurations;

export function mergeDurations(
  previous: Readonly<SpecDurations>,
  measured: Readonly<SpecDurations>,
  specNames: readonly string[],
): SpecDurations;

export function formatDurations(durations: Readonly<SpecDurations>): string;
