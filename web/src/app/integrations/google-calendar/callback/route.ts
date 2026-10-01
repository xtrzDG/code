/**
 * GET /integrations/google-calendar/callback?code=…&state=… — the end of
 * Google's consent page (forwarded by the API's public callback). The proxy
 * asks visitors without a session to sign in first. The values are sent to
 * the API with the owner's session: only the user who started connecting
 * can finish it, so a consent link forwarded to someone else cannot attach
 * their Google account to the sender's business.
 */

import { NextResponse, type NextRequest } from "next/server";

import { loginPath } from "@/lib/navigation";
import { callBackend } from "@/server/backend";
import {
  CALENDAR_CALLBACK_PATH,
  calendarReturnPath,
  readCalendarCallback,
  type CalendarCompletionOutcome,
} from "@/server/calendarCompletion";
import { clearSessionCookie, prepareBackendCall } from "@/server/relay";

export const dynamic = "force-dynamic";

const COMPLETION_TIMEOUT_MS = 30_000;

export async function GET(request: NextRequest): Promise<Response> {
  const here = `${CALENDAR_CALLBACK_PATH}${request.nextUrl.search}`;
  const prepared = prepareBackendCall(request, { useSession: true });
  if ("refusal" in prepared) {
    return prepared.refusal;
  }
  if (!prepared.token) {
    return NextResponse.redirect(new URL(loginPath({ next: here }), request.url));
  }

  prepared.headers.set("content-type", "application/json");
  let outcome: CalendarCompletionOutcome | null = null;
  try {
    const upstream = await callBackend("/v1/integrations/google-calendar/complete", {
      method: "POST",
      headers: prepared.headers,
      body: JSON.stringify(readCalendarCallback(request.nextUrl.searchParams)),
      timeoutMs: COMPLETION_TIMEOUT_MS,
    });
    if (upstream.status === 401) {
      const response = NextResponse.redirect(new URL(loginPath({ next: here, reason: "expired" }), request.url));
      clearSessionCookie(response);
      return response;
    }
    if (upstream.ok) {
      outcome = (await upstream.json()) as CalendarCompletionOutcome;
    }
  } catch {
    outcome = null;
  }
  return NextResponse.redirect(new URL(calendarReturnPath(outcome), request.url), 303);
}
