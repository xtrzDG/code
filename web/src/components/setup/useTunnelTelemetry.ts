"use client";

import { useEffect, useRef } from "react";

import { track } from "@/lib/track";
import { businessIdOfPath, tunnelStepReports } from "@/lib/tunnel/stepReports";
import type { TunnelPlace } from "@/lib/tunnel/steps";

/** Reports each screen of the tunnel the owner enters and completes (lib/tunnel/stepReports.ts). */
export function useTunnelTelemetry(place: TunnelPlace, pathname: string): void {
  const before = useRef<TunnelPlace | null>(null);
  useEffect(() => {
    const previous = before.current;
    before.current = place;
    for (const report of tunnelStepReports(previous, place, businessIdOfPath(pathname))) {
      track(report);
    }
  }, [place, pathname]);
}
