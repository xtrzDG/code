/** The notice Google Calendar's consent page returns with (`?calendar=…`). */

export const CALENDAR_FAILURE_REASONS = ["access_denied", "link_expired", "no_offline_access", "provider_error"] as const;

export type CalendarFailureReason = (typeof CALENDAR_FAILURE_REASONS)[number] | "unknown";

export type CalendarReturn = { kind: "connected" } | { kind: "error"; reason: CalendarFailureReason };

/**
 * What the API's Google callback said when it sent the owner back here
 * (?calendar=connected or ?calendar=error&reason=…); null otherwise.
 */
export function readCalendarReturn(search: string): CalendarReturn | null {
  const params = new URLSearchParams(search);
  const calendar = params.get("calendar");
  if (calendar === "connected") {
    return { kind: "connected" };
  }
  if (calendar !== "error") {
    return null;
  }
  const reason = params.get("reason");
  return {
    kind: "error",
    reason: (CALENDAR_FAILURE_REASONS as readonly string[]).includes(reason ?? "")
      ? (reason as CalendarFailureReason)
      : "unknown",
  };
}

/** The query without the calendar notice, to put back into the address bar. */
export function withoutCalendarReturn(search: string): string {
  const params = new URLSearchParams(search);
  params.delete("calendar");
  params.delete("reason");
  return params.toString();
}
