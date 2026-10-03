"use client";

import { useEffect, useState } from "react";

import { todayIn, type LocalDateText } from "./dates";

/**
 * Today in the business time zone, kept current: checked every minute and
 * when the tab becomes visible, so date filters ("Today", "Tomorrow", the
 * feed's period) move on at local midnight on a screen left open overnight.
 */
export function useToday(timeZone: string, intervalMs: number = 60_000): LocalDateText {
  const [state, setState] = useState(() => ({ timeZone, today: todayIn(timeZone) }));
  useEffect(() => {
    const check = () => {
      const today = todayIn(timeZone);
      setState((previous) =>
        previous.timeZone === timeZone && previous.today === today ? previous : { timeZone, today },
      );
    };
    const timer = window.setInterval(check, intervalMs);
    const onVisible = () => {
      if (document.visibilityState === "visible") {
        check();
      }
    };
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      window.clearInterval(timer);
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, [timeZone, intervalMs]);
  return state.timeZone === timeZone ? state.today : todayIn(timeZone);
}
