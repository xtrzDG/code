/**
 * The person's signed-in devices as Account → Security lists them: this
 * device first, then the most recently used.
 */

import type { UserSessionView } from "@/api/types";

/** This device first, then by last use (newest first). */
export function sortSessions(items: readonly UserSessionView[]): UserSessionView[] {
  return [...items].sort((left, right) => {
    if (left.is_current !== right.is_current) {
      return left.is_current ? -1 : 1;
    }
    return right.last_seen_at - left.last_seen_at;
  });
}

/** How many other devices "Sign out everywhere else" would sign out. */
export function otherSessionCount(items: readonly UserSessionView[]): number {
  return items.filter((item) => !item.is_current).length;
}

/** The list once one session is signed out (before the server answers again). */
export function withoutSession(items: readonly UserSessionView[], sessionId: string): UserSessionView[] {
  return items.filter((item) => item.id !== sessionId);
}

/** The list once every other session is signed out. */
export function onlyCurrent(items: readonly UserSessionView[]): UserSessionView[] {
  return items.filter((item) => item.is_current);
}
