"use client";

import { useSyncExternalStore } from "react";

const subscribeNever = () => () => undefined;

/**
 * False while rendering on the server and hydrating, true afterwards. For
 * values the server cannot know the same way as the browser (the browser's
 * list of time zones), so hydration does not mismatch.
 */
export function useIsClient(): boolean {
  return useSyncExternalStore(
    subscribeNever,
    () => true,
    () => false,
  );
}
