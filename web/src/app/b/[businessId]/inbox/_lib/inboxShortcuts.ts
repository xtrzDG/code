/**
 * The inbox's keyboard: j and k move through the list, Enter opens, e marks
 * the conversation resolved, a takes it, x selects it for a bulk action, /
 * goes to the search, ? shows these keys and Escape clears the selection.
 *
 * Keys are read only when they cannot mean typing: not in a text field, a
 * select or an editable area, not with Ctrl, Cmd or Alt, not while an input
 * method composes, and not over an open dialog.
 */

export type InboxShortcut = "next" | "previous" | "open" | "resolve" | "assign" | "select" | "search" | "help" | "clear";

/** The keys as the help sheet lists them, in its order. */
export const SHORTCUT_KEYS: readonly { keys: readonly string[]; action: InboxShortcut }[] = [
  { keys: ["j"], action: "next" },
  { keys: ["k"], action: "previous" },
  { keys: ["Enter"], action: "open" },
  { keys: ["e"], action: "resolve" },
  { keys: ["a"], action: "assign" },
  { keys: ["x"], action: "select" },
  { keys: ["/"], action: "search" },
  { keys: ["?"], action: "help" },
  { keys: ["Esc"], action: "clear" },
];

const KEY_ACTIONS: Readonly<Record<string, InboxShortcut>> = {
  j: "next",
  J: "next",
  k: "previous",
  K: "previous",
  Enter: "open",
  e: "resolve",
  E: "resolve",
  a: "assign",
  A: "assign",
  x: "select",
  X: "select",
  "/": "search",
  "?": "help",
  Escape: "clear",
};

/** What `aria-keyshortcuts` announces on the list. */
export const ARIA_KEY_SHORTCUTS = "J K Enter E A X / Shift+? Escape";

export interface KeyLike {
  key: string;
  ctrlKey: boolean;
  metaKey: boolean;
  altKey: boolean;
  isComposing: boolean;
  defaultPrevented: boolean;
}

export interface TargetLike {
  tagName: string;
  isContentEditable: boolean;
  type?: string;
}

const TEXT_INPUTS = new Set(["", "text", "search", "email", "tel", "url", "number", "password", "date", "time"]);

/** Whether a key on `target` would type, pick or edit something. */
export function isTypingTarget(target: TargetLike | null): boolean {
  if (!target) {
    return false;
  }
  const tag = target.tagName.toUpperCase();
  if (target.isContentEditable || tag === "TEXTAREA" || tag === "SELECT") {
    return true;
  }
  return tag === "INPUT" && TEXT_INPUTS.has((target.type ?? "").toLowerCase());
}

/**
 * The shortcut a key press means here, or null to leave it alone. Enter is
 * the list's only on its rows' cursor: on a focused link or button the
 * browser already opens or presses it (`onControl`).
 */
export function shortcutOf(
  event: KeyLike,
  target: TargetLike | null,
  { isDialogOpen, onControl }: { isDialogOpen: boolean; onControl: boolean },
): InboxShortcut | null {
  if (event.defaultPrevented || event.isComposing || event.ctrlKey || event.metaKey || event.altKey || isDialogOpen) {
    return null;
  }
  if (isTypingTarget(target)) {
    return null;
  }
  const action = KEY_ACTIONS[event.key] ?? null;
  if (action === "open" && onControl) {
    return null;
  }
  return action;
}
