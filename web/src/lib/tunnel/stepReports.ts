/**
 * What the tunnel tells the founder's metrics about a move between its
 * screens: the screen entered, and the one left when the move went deeper
 * (a step completed; going back completes nothing). The finale is no
 * screen of the tunnel. The business is named once it exists (/b/{id}/…);
 * the first two screens come before it.
 */

import type { TunnelStepReport } from "@/lib/track";

import { FINALE, direction, type TunnelPlace } from "./steps";

const BUSINESS_PATH = /^\/b\/([^/]+)\//;

export function businessIdOfPath(pathname: string): string | undefined {
  const match = BUSINESS_PATH.exec(pathname);
  if (!match?.[1]) {
    return undefined;
  }
  try {
    return decodeURIComponent(match[1]);
  } catch {
    return undefined;
  }
}

export function tunnelStepReports(
  before: TunnelPlace | null,
  place: TunnelPlace,
  businessId: string | undefined,
): TunnelStepReport[] {
  if (before === place) {
    return [];
  }
  const business = businessId === undefined ? {} : { business_id: businessId };
  const reports: TunnelStepReport[] = [];
  if (before !== null && before !== FINALE && direction(before, place) === 1) {
    reports.push({ kind: "tunnel_step", step: before, action: "completed", ...business });
  }
  if (place !== FINALE) {
    reports.push({ kind: "tunnel_step", step: place, action: "entered", ...business });
  }
  return reports;
}
