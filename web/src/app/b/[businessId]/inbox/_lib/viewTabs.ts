/**
 * How the inbox views share the row above the list: the three views staff
 * work from stay in sight (Needs a person, Requests, Mine); Unassigned and
 * All sit under "More". A view chosen from "More" takes the More button's
 * place in full, so the chosen view is never cut or scrolled away.
 */

import { INBOX_VIEWS, type InboxView } from "@/lib/navigation";

export const PRIMARY_INBOX_VIEWS = ["needs_person", "requests", "mine"] as const satisfies readonly InboxView[];

export const MORE_INBOX_VIEWS: readonly InboxView[] = INBOX_VIEWS.filter(
  (view) => !(PRIMARY_INBOX_VIEWS as readonly InboxView[]).includes(view),
);

export function isMoreInboxView(view: InboxView): boolean {
  return MORE_INBOX_VIEWS.includes(view);
}

/** The next menu item for a key (arrows wrap, Home and End jump); null for other keys. */
export function menuTarget(key: string, index: number, count: number): number | null {
  if (count === 0) {
    return null;
  }
  switch (key) {
    case "ArrowDown":
      return (index + 1) % count;
    case "ArrowUp":
      return (index - 1 + count) % count;
    case "Home":
      return 0;
    case "End":
      return count - 1;
    default:
      return null;
  }
}
