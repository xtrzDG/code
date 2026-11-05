/**
 * The owner's suggestion to set up a second factor, right after a sign-in
 * with the login code alone (the API's `second_factor_suggested`): a page
 * they may skip, shown at every such sign-in until they set one up. A
 * sign-in already headed to Account → Security goes straight there.
 */

import { ACCOUNT_SECURITY_PATH, HOME_PATH, safeNextPath } from "@/lib/navigation";

export const PROTECT_ACCOUNT_PATH = "/account/protect";

function isUnder(path: string, page: string): boolean {
  return path === page || path.startsWith(`${page}?`) || path.startsWith(`${page}/`);
}

/** Where a fresh sign-in goes: `next`, or the suggestion page before it. */
export function afterSignInPath(next: string, isSecondFactorSuggested: boolean): string {
  if (!isSecondFactorSuggested || isUnder(next, ACCOUNT_SECURITY_PATH) || isUnder(next, PROTECT_ACCOUNT_PATH)) {
    return next;
  }
  return `${PROTECT_ACCOUNT_PATH}?${new URLSearchParams({ next }).toString()}`;
}

/** The suggestion page's way on (`?next=`, kept on this site), home by default. */
export function suggestionNext(value: string | null | undefined): string {
  const next = safeNextPath(value, HOME_PATH);
  return isUnder(next, PROTECT_ACCOUNT_PATH) ? HOME_PATH : next;
}
