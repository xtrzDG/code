/**
 * Finishing a Google Calendar connection in the cabinet: Google (through
 * the API's public callback) sends the owner to
 * /integrations/google-calendar/callback?code=…&state=…; the cabinet sends
 * those values with the owner's session, so only the user who started
 * connecting can finish it, then opens the business's Channels page.
 */

import { HOME_PATH, businessPath } from "@/lib/navigation";

export const CALENDAR_CALLBACK_PATH = "/integrations/google-calendar/callback";

/** Google's callback values, as the API's completion route takes them. */
export interface CalendarCompletionBody {
  state?: string;
  code?: string;
  error?: string;
}

/** What the API answered: the business and why connecting failed, if it did. */
export interface CalendarCompletionOutcome {
  business_id?: string | null;
  failure?: string | null;
  connection?: unknown;
}

const CALLBACK_VALUES = ["state", "code", "error"] as const;

/** The non-blank callback values of the query. */
export function readCalendarCallback(params: URLSearchParams): CalendarCompletionBody {
  const body: CalendarCompletionBody = {};
  for (const name of CALLBACK_VALUES) {
    const value = params.get(name)?.trim();
    if (value) {
      body[name] = value;
    }
  }
  return body;
}

/**
 * Where the owner lands: the Channels page with ?calendar=connected or
 * ?calendar=error&reason=…; the businesses list when the business is not
 * known (an unknown or foreign link, or the API failed).
 */
export function calendarReturnPath(outcome: CalendarCompletionOutcome | null): string {
  const connected = outcome !== null && !outcome.failure && Boolean(outcome.connection);
  const query = new URLSearchParams(
    connected ? { calendar: "connected" } : { calendar: "error", reason: outcome?.failure || "provider_error" },
  );
  const path = outcome?.business_id ? businessPath(outcome.business_id, "channels") : HOME_PATH;
  return `${path}?${query.toString()}`;
}
