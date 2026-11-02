/**
 * After a step-up that raised the session from one factor to two
 * (`is_level_raised` of the API's answer), the cabinet's server swaps the
 * session's token (POST /api/auth/session/rotate, a new httpOnly cookie)
 * before the waiting requests run again, so a token copied before the
 * step-up never gains its level. Never throws: when the swap fails, the
 * session keeps its token and works on.
 */

export const ROTATE_SESSION_ROUTE = "/api/auth/session/rotate";

export async function rotateSessionIfRaised(assurance: { is_level_raised?: boolean } | undefined): Promise<void> {
  if (!assurance?.is_level_raised) {
    return;
  }
  try {
    await fetch(ROTATE_SESSION_ROUTE, { method: "POST" });
  } catch {
    // Offline: the session keeps its token.
  }
}
