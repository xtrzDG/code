import { describe, expect, it } from "vitest";

import { isTypingTarget, SHORTCUT_KEYS, shortcutOf, type KeyLike, type TargetLike } from "./inboxShortcuts";

const press = (key: string, patch: Partial<KeyLike> = {}): KeyLike => ({
  key,
  ctrlKey: false,
  metaKey: false,
  altKey: false,
  isComposing: false,
  defaultPrevented: false,
  ...patch,
});
const body: TargetLike = { tagName: "BODY", isContentEditable: false };
const link: TargetLike = { tagName: "A", isContentEditable: false };
const calm = { isDialogOpen: false, onControl: false };

describe("inbox shortcuts", () => {
  it("map the keys of the help sheet, in either case", () => {
    expect(shortcutOf(press("j"), body, calm)).toBe("next");
    expect(shortcutOf(press("K"), body, calm)).toBe("previous");
    expect(shortcutOf(press("e"), link, calm)).toBe("resolve");
    expect(shortcutOf(press("a"), link, calm)).toBe("assign");
    expect(shortcutOf(press("x"), link, calm)).toBe("select");
    expect(shortcutOf(press("/"), body, calm)).toBe("search");
    expect(shortcutOf(press("?"), body, calm)).toBe("help");
    expect(shortcutOf(press("Escape"), body, calm)).toBe("clear");
    expect(shortcutOf(press("q"), body, calm)).toBeNull();
  });

  it("leave Enter to a focused link or button, and open the cursor's row otherwise", () => {
    expect(shortcutOf(press("Enter"), body, calm)).toBe("open");
    expect(shortcutOf(press("Enter"), link, { isDialogOpen: false, onControl: true })).toBeNull();
  });

  it("never take keys while typing, composing, with a modifier, already handled, or over a dialog", () => {
    expect(shortcutOf(press("j"), { tagName: "TEXTAREA", isContentEditable: false }, calm)).toBeNull();
    expect(shortcutOf(press("j"), { tagName: "input", isContentEditable: false, type: "search" }, calm)).toBeNull();
    expect(shortcutOf(press("j"), { tagName: "DIV", isContentEditable: true }, calm)).toBeNull();
    expect(shortcutOf(press("j", { isComposing: true }), body, calm)).toBeNull();
    expect(shortcutOf(press("k", { ctrlKey: true }), body, calm)).toBeNull();
    expect(shortcutOf(press("k", { metaKey: true }), body, calm)).toBeNull();
    expect(shortcutOf(press("e", { altKey: true }), body, calm)).toBeNull();
    expect(shortcutOf(press("e", { defaultPrevented: true }), body, calm)).toBeNull();
    expect(shortcutOf(press("e"), body, { isDialogOpen: true, onControl: false })).toBeNull();
  });

  it("tell typing fields from controls that only choose", () => {
    expect(isTypingTarget(null)).toBe(false);
    expect(isTypingTarget({ tagName: "SELECT", isContentEditable: false })).toBe(true);
    expect(isTypingTarget({ tagName: "INPUT", isContentEditable: false })).toBe(true);
    expect(isTypingTarget({ tagName: "INPUT", isContentEditable: false, type: "checkbox" })).toBe(false);
    expect(isTypingTarget({ tagName: "INPUT", isContentEditable: false, type: "radio" })).toBe(false);
    expect(isTypingTarget(link)).toBe(false);
  });

  it("list every action once on the help sheet", () => {
    const actions = SHORTCUT_KEYS.map((entry) => entry.action);
    expect(new Set(actions).size).toBe(actions.length);
    expect(actions).toEqual(["next", "previous", "open", "resolve", "assign", "select", "search", "help", "clear"]);
  });
});
