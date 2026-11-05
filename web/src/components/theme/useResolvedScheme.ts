"use client";

import { useSyncExternalStore } from "react";

export type ResolvedScheme = "dark" | "light";

const DARK_QUERY = "(prefers-color-scheme: dark)";

function currentScheme(): ResolvedScheme {
  const theme = document.documentElement.dataset.theme;
  if (theme === "dark" || theme === "light") {
    return theme;
  }
  return window.matchMedia(DARK_QUERY).matches ? "dark" : "light";
}

function subscribe(onChange: () => void): () => void {
  const observer = new MutationObserver(onChange);
  observer.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
  const media = window.matchMedia(DARK_QUERY);
  media.addEventListener("change", onChange);
  return () => {
    observer.disconnect();
    media.removeEventListener("change", onChange);
  };
}

/**
 * The colour scheme the page shows now: the chosen theme, or the operating
 * system's for "system". For things CSS cannot colour (a WebGL scene).
 * The server (and the first render) assume dark, the default theme.
 */
export function useResolvedScheme(): ResolvedScheme {
  return useSyncExternalStore(subscribe, currentScheme, () => "dark");
}
