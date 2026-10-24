"use client";

import { useEffect, useState } from "react";

import { localNowIn } from "./bookingList";

/**
 * The business's local time now ("YYYY-MM-DDTHH:MM"), moved on every
 * minute, so an open dialog or the agenda crosses a booking's start.
 */
export function useLocalNow(timeZone: string): string {
  const [now, setNow] = useState(() => localNowIn(timeZone));
  useEffect(() => {
    const timer = window.setInterval(() => setNow(localNowIn(timeZone)), 60_000);
    return () => window.clearInterval(timer);
  }, [timeZone]);
  return now;
}
