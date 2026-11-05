"use client";

import { useEffect, useState } from "react";

/**
 * The time now (ms), moved on every 30 seconds while `isTicking` (a held
 * place counting down) and when the tab comes back into view.
 */
export function useMinuteClock(isTicking: boolean): number {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (!isTicking) {
      return undefined;
    }
    const tick = () => setNow(Date.now());
    const timer = window.setInterval(tick, 30_000);
    const onVisible = () => {
      if (document.visibilityState === "visible") {
        tick();
      }
    };
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      window.clearInterval(timer);
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, [isTicking]);
  return now;
}
