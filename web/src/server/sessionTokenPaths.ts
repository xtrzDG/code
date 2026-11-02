import "server-only";

/**
 * API answers that carry a session token: the sign-in steps and the
 * rotation after a raising proof. The cabinet's server reads them itself
 * (sessionOpeningRelay.ts, sessionRotation.ts) and puts the token into the
 * httpOnly cookie, so the generic relay (/api/backend/*) never hands one
 * to the browser as it is: page code never holds a session token.
 */

const SESSION_TOKEN_PATHS: ReadonlySet<string> = new Set([
  "/v1/auth/otp/verify",
  "/v1/auth/mfa/verify",
  "/v1/auth/mfa/passkey/verify",
  "/v1/auth/mfa/passkey/enroll/finish",
  "/v1/auth/session/rotate",
]);

/**
 * True when `backendPath` (as the relay sends it, percent-encoded) reaches
 * one of those routes. The API routes on the decoded path, so an encoded
 * slash ("session%2Frotate") or a doubled or trailing one counts too; a
 * path that cannot be decoded is refused as well.
 */
export function answersWithSessionToken(backendPath: string): boolean {
  let decoded: string;
  try {
    decoded = decodeURIComponent(backendPath.split("?")[0] ?? "");
  } catch {
    return true;
  }
  const segments = decoded.split("/").filter((segment) => segment !== "");
  return SESSION_TOKEN_PATHS.has(`/${segments.join("/")}`);
}
