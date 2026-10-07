/**
 * Small pieces of the autosave loop: which fields of two forms differ,
 * which failures are worth trying again, and the clock (injected, so tests
 * move time by hand instead of waiting).
 */

import type { ApiError } from "@/api/errors";

export interface AutosaveClock {
  now: () => number;
  setTimeout: (callback: () => void, delayMs: number) => unknown;
  clearTimeout: (handle: unknown) => void;
}

export const systemClock: AutosaveClock = {
  now: () => Date.now(),
  setTimeout: (callback, delayMs) => globalThis.setTimeout(callback, delayMs),
  clearTimeout: (handle) => globalThis.clearTimeout(handle as ReturnType<typeof setTimeout>),
};

/** The fields whose values differ (arrays and objects compared by value). */
export function changedFields<Form extends object>(left: Form, right: Form): (keyof Form)[] {
  const keys = new Set([...Object.keys(left), ...Object.keys(right)]) as Set<keyof Form>;
  return [...keys].filter((key) => JSON.stringify(left[key]) !== JSON.stringify(right[key]));
}

const TRANSIENT_CODES = new Set(["network_error", "backend_unavailable", "external_service_error", "internal_error", "rate_limited"]);

/** A failure that may pass on its own (no connection, the server busy or down): tried again later. */
export function isTransientFailure(error: ApiError): boolean {
  return error.status === 0 || error.status >= 500 || TRANSIENT_CODES.has(error.code);
}
