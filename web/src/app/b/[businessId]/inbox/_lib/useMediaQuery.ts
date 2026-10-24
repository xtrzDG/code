"use client";

import { useSyncExternalStore } from "react";

/**
 * Whether a media query matches now, following changes (window resized,
 * phone turned). False on the server and in the first render, so the
 * page renders the narrow layout first and widens after hydration.
 */
export function useMediaQuery(query: string): boolean {
  return useSyncExternalStore(
    (onChange) => {
      const media = window.matchMedia(query);
      media.addEventListener("change", onChange);
      return () => media.removeEventListener("change", onChange);
    },
    () => window.matchMedia(query).matches,
    () => false,
  );
}

/** Tailwind's 2xl: a third column for the details beside the conversation. */
export const WIDE_PANEL_QUERY = "(min-width: 96rem)";
