/**
 * Signing out on this device: the session ends on the server
 * (POST /api/auth/logout, whose answer also carries Clear-Site-Data), and
 * this tab forgets what the session left in Web Storage itself, for
 * browsers that do not honour that header: the assistant's test chat
 * (session storage), the drafts, hidden hints and device settings (local
 * storage). The caller then loads the sign-in page in full.
 */

/** Empty this site's local and session storage; a browser that blocks storage has nothing to empty. */
function clearSiteStorage(): void {
  for (const storage of [() => window.localStorage, () => window.sessionStorage]) {
    try {
      storage().clear();
    } catch {
      // Storage unavailable (private mode, blocked): nothing was kept.
    }
  }
}

/**
 * Empty this tab's session storage (the assistant's test chat): a new
 * sign-in never finds what an earlier session in this tab left there.
 */
export function clearSessionStorage(): void {
  try {
    window.sessionStorage.clear();
  } catch {
    // Storage unavailable: nothing was kept.
  }
}

/** End the session and forget its traces in this browser; never throws. */
export async function signOut(): Promise<void> {
  try {
    await fetch("/api/auth/logout", { method: "POST" });
  } catch {
    // Offline: the cookie stays until it expires, the storage goes now.
  } finally {
    clearSiteStorage();
  }
}
