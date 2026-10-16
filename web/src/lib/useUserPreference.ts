"use client";

import { useCallback, useSyncExternalStore } from "react";

import { browserStorage, readPreference, subscribePreferences, writePreference } from "./userPreference";

/**
 * A choice of the signed-in person remembered in this browser
 * (lib/userPreference.ts): its stored text, null on the server, while
 * hydrating and when nothing is remembered, so the first paint is the
 * default and matches the server's; and a setter (null forgets it).
 */
export function useUserPreference(name: string, userId: string): [string | null, (value: string | null) => void] {
  const stored = useSyncExternalStore(
    subscribePreferences,
    () => readPreference(browserStorage(), name, userId),
    () => null,
  );
  const set = useCallback((value: string | null) => writePreference(browserStorage(), name, userId, value), [name, userId]);
  return [stored, set];
}
