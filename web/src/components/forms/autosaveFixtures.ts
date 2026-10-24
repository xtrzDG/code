/**
 * Test helpers of the autosave loop: a clock moved by hand, saves the test
 * answers one by one (a save stays open until the test settles it, so the
 * order of saves is proven, not timed), and a small settings form.
 */

import { ApiError, type ApiErrorCode } from "@/api/errors";
import type { MutationResult } from "@/api/mutations";

import { AutosaveEngine } from "./autosaveEngine";
import type { AutosaveClock } from "./autosaveParts";
import type { AutosaveConfig } from "./autosaveTypes";

function manualClock(): AutosaveClock & { advance: (ms: number) => void; pending: () => number } {
  let now = 1_000;
  let nextId = 1;
  const timers = new Map<number, { at: number; callback: () => void }>();
  return {
    now: () => now,
    setTimeout: (callback, delayMs) => {
      const id = nextId++;
      timers.set(id, { at: now + delayMs, callback });
      return id;
    },
    clearTimeout: (handle) => {
      timers.delete(handle as number);
    },
    advance: (ms) => {
      now += ms;
      for (const [id, timer] of [...timers.entries()].sort((left, right) => left[1].at - right[1].at)) {
        if (timer.at <= now && timers.has(id)) {
          timers.delete(id);
          timer.callback();
        }
      }
    },
    pending: () => timers.size,
  };
}

/** Saves that wait for the test: `next()` is the oldest open one. */
export function heldSaves<Body, Stored>() {
  const open: { body: Body; base: Stored; settle: (result: MutationResult<Stored>) => void }[] = [];
  const calls: Body[] = [];
  return {
    save: (body: Body, base: Stored) =>
      new Promise<MutationResult<Stored>>((resolve) => {
        calls.push(body);
        open.push({ body, base, settle: resolve });
      }),
    calls,
    open: () => open.length,
    next: () => {
      const first = open.shift();
      if (!first) {
        throw new Error("No save is waiting.");
      }
      return first;
    },
  };
}

export function apiError(code: ApiErrorCode, status: number, reason?: string): ApiError {
  return new ApiError({
    status,
    code,
    reasons: reason ? [{ code: reason, message: reason, details: [] }] : [],
  });
}

/** Lets pending promise callbacks run. */
export async function settled(): Promise<void> {
  for (let round = 0; round < 5; round += 1) {
    await Promise.resolve();
  }
}

export interface Stored {
  revision: number;
  name: string;
  days: number;
  isOn: boolean;
}

export type Values = Omit<Stored, "revision">;

const toForm = ({ name, days, isOn }: Stored): Values => ({ name, days, isOn });

function changesOf(form: Values, base: Stored): Partial<Values> | null {
  const changes = Object.fromEntries(
    (Object.keys(form) as (keyof Values)[]).filter((key) => form[key] !== base[key]).map((key) => [key, form[key]]),
  ) as Partial<Values>;
  return Object.keys(changes).length > 0 ? changes : null;
}

export function engineWith(
  stored: Stored,
  config: Omit<AutosaveConfig<Values, Stored, Partial<Values>>, "toForm" | "toBody"> &
    Partial<Pick<AutosaveConfig<Values, Stored, Partial<Values>>, "toBody">>,
  clock = manualClock(),
) {
  const engine = new AutosaveEngine<Values, Stored, Partial<Values>>(stored, toForm, clock);
  engine.configure({ toForm, toBody: changesOf, ...config });
  return { engine, clock };
}
