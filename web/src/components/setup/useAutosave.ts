"use client";

/**
 * Saves a screen's answers by themselves: a moment after the owner stops
 * typing (`delayMs`), and at once when they continue (`flush`). Only a
 * value that changed since the last save is sent, only a valid one, and
 * never two saves of the same screen at once (the later waits for the
 * earlier). Saves are reported to the top bar ("Saving…", "Saved").
 */

import { useCallback, useEffect, useRef } from "react";

import { useSaveTracker } from "./SaveTracker";

export interface AutosaveOptions<T> {
  delayMs?: number;
  /** False until the screen's data is loaded (nothing to compare with yet). */
  enabled?: boolean;
  /** A value that cannot be saved yet waits (the screen shows why on Continue). */
  isValid?: (value: T) => boolean;
}

export function useAutosave<T>(value: T, save: (value: T) => Promise<boolean>, options: AutosaveOptions<T> = {}) {
  const { delayMs = 900, enabled = true, isValid } = options;
  const track = useSaveTracker();
  const key = JSON.stringify(value);
  const saved = useRef<string | null>(null);
  const inFlight = useRef<Promise<boolean>>(Promise.resolve(true));
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const latest = useRef({ value, key, save, isValid });

  useEffect(() => {
    latest.current = { value, key, save, isValid };
  });

  const run = useCallback((force = false): Promise<boolean> => {
    const { value: current, key: currentKey, save: saveNow, isValid: valid } = latest.current;
    if ((!force && currentKey === saved.current) || (valid && !valid(current))) {
      return inFlight.current;
    }
    const previous = inFlight.current;
    // After the save before it, so two saves of one screen never cross.
    const next = previous.then(async () => {
      const ok = await track(saveNow(current));
      if (ok) {
        saved.current = currentKey;
      }
      return ok;
    });
    inFlight.current = next;
    return next;
  }, [track]);

  // The first value is what is stored: only changes after it are saved.
  useEffect(() => {
    if (enabled && saved.current === null) {
      saved.current = key;
    }
  }, [enabled, key]);

  useEffect(() => {
    if (!enabled || saved.current === null || key === saved.current) {
      return;
    }
    timer.current = setTimeout(() => void run(), delayMs);
    return () => {
      if (timer.current) {
        clearTimeout(timer.current);
      }
    };
  }, [enabled, key, delayMs, run]);

  /**
   * Save now what is not saved yet, and wait for every save of the screen.
   * `force` saves the value even unchanged (suggestions shown but never stored).
   */
  const flush = useCallback(
    async (options: { force?: boolean } = {}): Promise<boolean> => {
      if (timer.current) {
        clearTimeout(timer.current);
        timer.current = null;
      }
      return run(options.force ?? false);
    },
    [run],
  );

  return { flush };
}
