"use client";

/**
 * Saving the lines of a list one by one (the offer table, the ready
 * answers): saves of one line queue behind each other, so a line is never
 * created twice; `later` saves a line a moment after the typing in it
 * stops; with `flushOnLeave` every line is saved once more when the
 * screen goes away (`saveNow` sends nothing for a line that did not
 * change).
 */

import { useCallback, useEffect, useRef } from "react";

export interface LineSaveOptions {
  /** How long `later` waits after the last change of a line. */
  delayMs?: number;
  flushOnLeave?: boolean;
  /** The keys of the lines on screen when it goes away. */
  keys?: () => readonly string[];
}

const DEFAULT_DELAY_MS = 1_200;

export function useLineSaves(saveNow: (key: string) => Promise<boolean>, options: LineSaveOptions = {}) {
  const { delayMs = DEFAULT_DELAY_MS, flushOnLeave = false } = options;
  const queue = useRef(new Map<string, Promise<boolean>>());
  const timers = useRef(new Map<string, ReturnType<typeof setTimeout>>());
  const latest = useRef({ saveNow, keys: options.keys });
  useEffect(() => {
    latest.current = { saveNow, keys: options.keys };
  });

  const cancel = useCallback((key: string) => {
    clearTimeout(timers.current.get(key));
    timers.current.delete(key);
  }, []);

  /** Save one line now (after any save of it still running); false when it is not valid yet or failed. */
  const save = useCallback(
    (key: string): Promise<boolean> => {
      cancel(key);
      const next = (queue.current.get(key) ?? Promise.resolve(true)).then(() => latest.current.saveNow(key));
      queue.current.set(key, next);
      return next;
    },
    [cancel],
  );

  /** Save one line a moment after the owner stops typing in it. */
  const later = useCallback(
    (key: string) => {
      cancel(key);
      timers.current.set(
        key,
        setTimeout(() => void save(key), delayMs),
      );
    },
    [cancel, delayMs, save],
  );

  /** Waits for the saves of a line still running (before it is removed). */
  const settle = useCallback(
    async (key: string) => {
      cancel(key);
      await queue.current.get(key);
    },
    [cancel],
  );

  useEffect(() => {
    if (!flushOnLeave) {
      return;
    }
    const pending = timers.current;
    return () => {
      pending.forEach((timer) => clearTimeout(timer));
      pending.clear();
      (latest.current.keys?.() ?? []).forEach((key) => void save(key));
    };
  }, [flushOnLeave, save]);

  return { save, later, settle };
}
