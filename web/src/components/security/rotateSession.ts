/**
 * After a proof that raised the session from one factor to two
 * (`is_level_raised` of the API's answer: a step-up, a new authenticator
 * or a first passkey), the cabinet's server swaps the session's token
 * (POST /api/auth/session/rotate with the answer's one-time
 * `rotation_ticket`, a new httpOnly cookie) before the waiting requests
 * run again or the page reloads its data: only the new token carries the
 * two factors, so a token copied before never gains them. Never throws:
 * when the swap fails, the session keeps its token (one factor) and works
 * on; the next sensitive action asks to confirm again.
 */

export const ROTATE_SESSION_ROUTE = "/api/auth/session/rotate";

export async function rotateSessionIfRaised(
  answer: { is_level_raised?: boolean; rotation_ticket?: string | null } | undefined,
): Promise<void> {
  if (!answer?.is_level_raised || !answer.rotation_ticket) {
    return;
  }
  try {
    await fetch(ROTATE_SESSION_ROUTE, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ rotation_ticket: answer.rotation_ticket }),
    });
  } catch {
    // Offline: the session keeps its token.
  }
}
