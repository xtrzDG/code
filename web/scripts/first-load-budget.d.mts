/** Types of scripts/first-load-budget.mjs for its tests (src/test/firstLoadBudget.test.ts). */

export interface FirstLoadBudget {
  /** Kilobytes (1024 bytes) of gzipped first-load JavaScript per page. */
  pages: Record<string, number>;
  /** Kilobytes of the one lazy chunk with three.js. */
  lazy3dChunk: number;
}

export interface FirstLoadMeasurement {
  pages: readonly { page: string; gzip: number }[];
  lazyChunks: readonly { name: string; gzip: number }[];
}

export function parseBudget(raw: unknown): FirstLoadBudget;

export function overBudget(budget: FirstLoadBudget, measured: FirstLoadMeasurement): string[];
