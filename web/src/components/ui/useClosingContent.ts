"use client";

import { useEffect, useState } from "react";

/** A little longer than a dialog's closing fade (`--motion-fast` in src/styles/motion.css). */
export const DIALOG_CLOSE_MS = 220;

/**
 * Keeps a closing dialog's content on screen while it fades out.
 *
 * Dialogs render their content only while open (closed ones hold no state
 * and run no queries). When `open` turns false the parent often clears what
 * the content was about (the selected lead), so this returns the parts the
 * dialog showed when it was last open, and `isMounted` stays true until the
 * fade has played; then the content goes away as before.
 *
 *     const closing = useClosingContent(open, [title, footer, children] as const);
 *     const [shownTitle, shownFooter, shownChildren] = closing.content;
 *     {closing.isMounted ? …shownChildren… : null}
 */
export function useClosingContent<Parts extends readonly unknown[]>(
  open: boolean,
  parts: Parts,
): { content: Parts; isMounted: boolean } {
  const [kept, setKept] = useState(parts);
  const [wasOpen, setWasOpen] = useState(open);
  const [isClosing, setClosing] = useState(false);

  // Derived from props during render (React's "previous props" pattern), not in an effect.
  if (wasOpen !== open) {
    setWasOpen(open);
    setClosing(!open);
  }
  if (open && parts.some((part, index) => part !== kept[index])) {
    setKept(parts);
  }

  useEffect(() => {
    if (!isClosing) {
      return;
    }
    const timer = window.setTimeout(() => setClosing(false), DIALOG_CLOSE_MS);
    return () => window.clearTimeout(timer);
  }, [isClosing]);

  return { content: open ? parts : kept, isMounted: open || isClosing };
}
