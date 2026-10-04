"use client";

import { useSyncExternalStore } from "react";

/**
 * Whether a media query matches now, following changes (window resized,
 * phone turned). False on the server and while hydrating, so nothing that
 * depends on it runs before the screen is known.
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

/** Below the cabinet's large screens (Tailwind's lg, 64rem): the phone layout. */
export const COMPACT_SCREEN_QUERY = "(max-width: 63.98rem)";
/** The cabinet's large screens (Tailwind's lg). */
export const WIDE_SCREEN_QUERY = "(min-width: 64rem)";
