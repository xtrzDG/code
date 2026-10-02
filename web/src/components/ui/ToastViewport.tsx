"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

import { cn } from "@/lib/cn";

import { IconAlert, IconCheck, IconInfo, IconX } from "../icons";

export type ToastTone = "success" | "error" | "info";

export interface ToastItem {
  id: number;
  tone: ToastTone;
  title: string;
  description?: string | null;
  action?: { label: string; onAction: () => void };
  durationMs: number;
}

const TONE_STYLES: Record<ToastTone, { icon: typeof IconCheck; className: string }> = {
  success: { icon: IconCheck, className: "text-success" },
  error: { icon: IconAlert, className: "text-danger" },
  info: { icon: IconInfo, className: "text-info" },
};

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

/** Closes the toast after its time; the time stands still while `isPaused`. */
function useDismissTimer(durationMs: number, isPaused: boolean, onExpire: () => void): void {
  const remaining = useRef(durationMs);
  const onExpireRef = useRef(onExpire);
  useEffect(() => {
    onExpireRef.current = onExpire;
  });

  useEffect(() => {
    if (isPaused) {
      return;
    }
    const startedAt = Date.now();
    const timer = window.setTimeout(() => onExpireRef.current(), remaining.current);
    return () => {
      window.clearTimeout(timer);
      remaining.current = Math.max(0, remaining.current - (Date.now() - startedAt));
    };
  }, [isPaused]);
}

function ToastCard({ item, onDismiss, closeLabel }: { item: ToastItem; onDismiss: (id: number) => void; closeLabel: string }) {
  const [isHovered, setHovered] = useState(false);
  const [isFocused, setFocused] = useState(false);
  // Only a toast with an action (Undo) waits while it is pointed at or
  // focused: someone is reaching for the button. A plain message keeps its
  // time, so it never sits on top of what the person clicks next.
  const isPaused = item.action !== undefined && (isHovered || isFocused);
  useDismissTimer(item.durationMs, isPaused, () => onDismiss(item.id));
  const { icon: Icon, className } = TONE_STYLES[item.tone];

  return (
    <div
      role={item.tone === "error" ? "alert" : "status"}
      onPointerEnter={() => setHovered(true)}
      onPointerLeave={() => setHovered(false)}
      onFocus={() => setFocused(true)}
      onBlur={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget as Node | null)) {
          setFocused(false);
        }
      }}
      className="pointer-events-auto relative flex w-full max-w-sm origin-bottom animate-toast-in items-start gap-3 overflow-hidden rounded-xl border border-line bg-surface p-3.5 shadow-lg"
    >
      <Icon className={cn("mt-0.5 size-5 shrink-0", className)} aria-hidden />
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium text-ink">{item.title}</p>
        {item.description ? <p className="mt-1 text-sm break-words text-ink-muted">{item.description}</p> : null}
      </div>
      {item.action ? (
        <button
          type="button"
          onClick={() => {
            onDismiss(item.id);
            item.action?.onAction();
          }}
          className="-my-1 shrink-0 rounded-md px-2 py-1 text-sm font-semibold text-accent transition-colors hover:bg-accent-soft focus-visible:outline-2 focus-visible:outline-focus"
        >
          {item.action.label}
        </button>
      ) : null}
      <button
        type="button"
        onClick={() => onDismiss(item.id)}
        className="-m-1 rounded-md p-1 text-ink-subtle hover:bg-surface-muted hover:text-ink focus-visible:outline-2 focus-visible:outline-focus"
        aria-label={closeLabel}
      >
        <IconX className="size-4" aria-hidden />
      </button>
      {item.action ? (
        // The undo window running down; it stops while the toast is paused.
        <span
          aria-hidden
          className="absolute inset-x-0 bottom-0 h-0.5 origin-left animate-countdown bg-accent-solid/70 motion-reduce:hidden"
          style={{ animationDuration: `${item.durationMs}ms`, animationPlayState: isPaused ? "paused" : "running" }}
        />
      ) : null}
    </div>
  );
}

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
  const viewport = (
    <div
      className="pointer-events-none fixed inset-x-0 bottom-0 z-[60] flex flex-col items-center gap-2 p-4 sm:items-end"
      aria-live="polite"
      aria-relevant="additions"
    >
      {items.map((item) => (
        <ToastCard key={item.id} item={item} onDismiss={onDismiss} closeLabel={closeLabel} />
      ))}
    </div>
  );
  // Fixed positioning inside the dialog still refers to the viewport (the
  // dialog has no transform), so the corner does not move.
  return topDialog ? createPortal(viewport, topDialog) : viewport;
}
