"use client";

import { useEffect, useEffectEvent } from "react";

/**
 * Reloads a live list (conversations, handoffs) every `intervalMs` while the
 * tab is visible, and right away when the user comes back to the tab.
 */
export function useAutoReload(reload: () => void, intervalMs: number = 60_000): void {
  const onTick = useEffectEvent(() => {
    if (document.visibilityState === "visible") {
      reload();
    }
  });

  useEffect(() => {
    const timer = window.setInterval(onTick, intervalMs);
    const onVisible = () => {
      if (document.visibilityState === "visible") {
        onTick();
      }
    };
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      window.clearInterval(timer);
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, [intervalMs]);
}
