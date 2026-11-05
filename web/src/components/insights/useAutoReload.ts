"use client";

import { useEffect, useEffectEvent } from "react";

/**
 * Reloads a live list right away when the user comes back to the tab, and,
 * with `intervalMs`, also every `intervalMs` while the tab is visible.
 *
 * Lists whose every load is written to the audit log (conversations,
 * handoffs: views of personal data) must not poll: they pass
 * `intervalMs: null` and reload only on return and with the Refresh button,
 * so an open tab does not add an audit entry every minute.
 */
export function useAutoReload(reload: () => void, options: { intervalMs: number | null } = { intervalMs: 60_000 }): void {
  const { intervalMs } = options;
  const onTick = useEffectEvent(() => {
    if (document.visibilityState === "visible") {
      reload();
    }
  });

  useEffect(() => {
    const timer = intervalMs === null ? null : window.setInterval(onTick, intervalMs);
    const onVisible = () => {
      if (document.visibilityState === "visible") {
        onTick();
      }
    };
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      if (timer !== null) {
        window.clearInterval(timer);
      }
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, [intervalMs]);
}
