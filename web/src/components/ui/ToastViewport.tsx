"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

import type { SentenceWithUserValues } from "@/i18n/userValues";

import { useToastList } from "./toastList";

export type ToastTone = "success" | "error" | "info";

/**
 * The interface's text, or a sentence that names user content ("Тамар
 * handles this conversation now": `{ text: t(key), values: { name } }`),
 * shown with `UserSentence`.
 */
export type ToastTitle = string | SentenceWithUserValues;

export interface ToastItem {
  id: number;
  tone: ToastTone;
  title: ToastTitle;
  description?: string | null;
  action?: { label: string; onAction: () => void };
  durationMs: number;
}

/**
 * The modal dialog on top of the top layer, or null. Dialogs are stacked in
 * the order they were opened; one opened later covers the earlier ones.
 * `recheck` (the visible toasts) re-reads the stack, which also drops a
 * dialog that was removed from the page while open.
 */
function useTopModalDialog(recheck: unknown): HTMLDialogElement | null {
  const [top, setTop] = useState<HTMLDialogElement | null>(null);
  const stack = useRef<HTMLDialogElement[]>([]);

  const sync = useCallback(() => {
    const dialogs = stack.current.filter((dialog) => dialog.isConnected && dialog.matches(":modal"));
    for (const dialog of document.querySelectorAll<HTMLDialogElement>("dialog:modal")) {
      if (!dialogs.includes(dialog)) {
        dialogs.push(dialog);
      }
    }
    stack.current = dialogs;
    setTop(dialogs.at(-1) ?? null);
  }, []);

  useEffect(() => {
    // Only the "open" attribute is watched (showModal() / close()), which is cheap.
    const observer = new MutationObserver(sync);
    observer.observe(document.body, { subtree: true, attributes: true, attributeFilter: ["open"] });
    return () => observer.disconnect();
  }, [sync]);

  useEffect(() => {
    sync();
  }, [recheck, sync]);

  return top;
}

/**
 * The corner the toasts appear in: a live region that is always on the
 * page (so screen readers announce what is added to it), with the
 * animated list (ToastList.tsx) loaded into it when the first toast comes.
 */
export function ToastViewport({
  items,
  onDismiss,
  closeLabel,
}: {
  items: ToastItem[];
  onDismiss: (id: number) => void;
  closeLabel: string;
}) {
  const topDialog = useTopModalDialog(items);
  const renderList = useToastList(items.length > 0);
  const viewport = (
    <div
      className="pointer-events-none fixed inset-x-0 bottom-0 z-[60] flex flex-col items-center gap-2 p-4 sm:items-end"
      aria-live="polite"
      aria-relevant="additions"
    >
      {renderList ? renderList({ items, onDismiss, closeLabel }) : null}
    </div>
  );
  // Fixed positioning inside the dialog still refers to the viewport (the
  // dialog has no transform once it has sprung in), so the corner does not move.
  return topDialog ? createPortal(viewport, topDialog) : viewport;
}
