/**
 * The person's choices about the cabinet's frame that the server must know
 * for the first paint: whether the desktop sidebar is collapsed to icons.
 * Kept in a cookie (a year), so the page never jumps after loading.
 */

export const SIDEBAR_COOKIE = "aw_sidebar";

export type SidebarState = "expanded" | "collapsed";

const YEAR_SECONDS = 365 * 24 * 60 * 60;

/** The cookie's value as a state; anything unknown is the default, expanded. */
export function readSidebarState(value: string | null | undefined): SidebarState {
  return value === "collapsed" ? "collapsed" : "expanded";
}

/** `document.cookie = sidebarCookie("collapsed")`. */
export function sidebarCookie(state: SidebarState): string {
  return `${SIDEBAR_COOKIE}=${state}; Path=/; Max-Age=${YEAR_SECONDS}; SameSite=Lax`;
}
