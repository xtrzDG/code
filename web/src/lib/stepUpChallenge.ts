/**
 * The API's "confirm it is you" refusal of a sensitive action (step-up):
 * 401 with `WWW-Authenticate: Bearer error="insufficient_user_authentication"`
 * (RFC 9470). Unlike any other 401, the session is still valid: the
 * cabinet's proxy keeps the cookie and the page asks for a code.
 */

export const STEP_UP_CHALLENGE_ERROR = "insufficient_user_authentication";

export function isStepUpChallenge(status: number, headers: Headers): boolean {
  return status === 401 && (headers.get("www-authenticate") ?? "").includes(STEP_UP_CHALLENGE_ERROR);
}
