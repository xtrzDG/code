"use client";

/**
 * Short notifications in the corner of the screen.
 *
 *     const toast = useToast();
 *     toast.success(t("common.saved"));
 *     toast.error(apiError);                      // localized by error code
 *     toast.error(apiError, { conflict: "bookings.slotTaken" });
 *
 * While a modal <dialog> is open (Modal, the phone menu) everything outside
 * it is inert and drawn below it, so the toasts move into the topmost open
 * dialog: they stay visible and can be dismissed.
 */

import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";

import { describeError, type ErrorMessageOverrides } from "@/api/errors";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";

import { IconAlert, IconCheck, IconInfo, IconX } from "../icons";

export type ToastTone = "success" | "error" | "info";

interface ToastItem {
  id: number;
  tone: ToastTone;
  title: string;
  description?: string | null;
}

export interface ToastApi {
  show: (toast: { tone: ToastTone; title: string; description?: string | null; durationMs?: number }) => void;
  success: (title: string, description?: string) => void;
  info: (title: string, description?: string) => void;
  /** An ApiError (or anything thrown) as a localized message. */
  error: (error: unknown, overrides?: ErrorMessageOverrides) => void;
  dismiss: (id: number) => void;
}

const ToastContext = createContext<ToastApi | null>(null);

const DEFAULT_DURATION_MS = 5_000;
const ERROR_DURATION_MS = 9_000;
const MAX_VISIBLE = 4;

export function ToastProvider({ children }: { children: ReactNode }) {
  const { t } = useI18n();
  const [items, setItems] = useState<ToastItem[]>([]);
  const nextId = useRef(1);

  const dismiss = useCallback((id: number) => {
    setItems((current) => current.filter((item) => item.id !== id));
  }, []);

  const show = useCallback<ToastApi["show"]>(
    ({ tone, title, description, durationMs }) => {
      const id = nextId.current++;
      setItems((current) => [...current, { id, tone, title, description }].slice(-MAX_VISIBLE));
      window.setTimeout(
        () => dismiss(id),
        durationMs ?? (tone === "error" ? ERROR_DURATION_MS : DEFAULT_DURATION_MS),
      );
    },
    [dismiss],
  );

  const api = useMemo<ToastApi>(
    () => ({
      show,
      dismiss,
      success: (title, description) => show({ tone: "success", title, description }),
      info: (title, description) => show({ tone: "info", title, description }),
      error: (error, overrides) => {
        const { title, detail, requestId } = describeError(error, t, overrides);
        const lines = [detail, requestId ? t("common.requestId", { id: requestId }) : null].filter(Boolean);
        show({ tone: "error", title, description: lines.join(" · ") || null });
      },
    }),
    [show, dismiss, t],
  );

  return (
    <ToastContext.Provider value={api}>
      {children}
      <ToastViewport items={items} onDismiss={dismiss} closeLabel={t("common.close")} />
    </ToastContext.Provider>
  );
}

const TONE_STYLES: Record<ToastTone, { icon: typeof IconCheck; className: string }> = {
  success: { icon: IconCheck, className: "text-success" },
  error: { icon: IconAlert, className: "text-danger" },
  info: { icon: IconInfo, className: "text-info" },
};

/**
 * The modal dialog on top of the top layer, or null. Dialogs are stacked in
 * the order they were opened; one opened later covers the earlier ones.
 */
function useTopModalDialog(): HTMLDialogElement | null {
  const [top, setTop] = useState<HTMLDialogElement | null>(null);

  useEffect(() => {
    const stack: HTMLDialogElement[] = [];
    const sync = () => {
      for (let index = stack.length - 1; index >= 0; index -= 1) {
        const dialog = stack[index];
        if (!dialog || !dialog.isConnected || !dialog.matches(":modal")) {
          stack.splice(index, 1);
        }
      }
      for (const dialog of document.querySelectorAll<HTMLDialogElement>("dialog:modal")) {
        if (!stack.includes(dialog)) {
          stack.push(dialog);
        }
      }
      setTop(stack.at(-1) ?? null);
    };
    const observer = new MutationObserver(sync);
    // "open" flips on showModal()/close(); childList catches a dialog that
    // is removed while open.
    observer.observe(document.body, { subtree: true, childList: true, attributes: true, attributeFilter: ["open"] });
    sync();
    return () => observer.disconnect();
  }, []);

  return top;
}

function ToastViewport({
  items,
  onDismiss,
  closeLabel,
}: {
  items: ToastItem[];
  onDismiss: (id: number) => void;
  closeLabel: string;
}) {
  const topDialog = useTopModalDialog();
  const viewport = (
    <div
      className="pointer-events-none fixed inset-x-0 bottom-0 z-[60] flex flex-col items-center gap-2 p-4 sm:items-end"
      aria-live="polite"
      aria-relevant="additions"
    >
      {items.map((item) => {
        const { icon: Icon, className } = TONE_STYLES[item.tone];
        return (
          <div
            key={item.id}
            role={item.tone === "error" ? "alert" : "status"}
            className="pointer-events-auto flex w-full max-w-sm items-start gap-3 rounded-xl border border-line bg-surface p-4 shadow-lg shadow-black/5"
          >
            <Icon className={cn("mt-0.5 size-5 shrink-0", className)} aria-hidden />
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium text-ink">{item.title}</p>
              {item.description ? (
                <p className="mt-1 break-words text-sm text-ink-muted">{item.description}</p>
              ) : null}
            </div>
            <button
              type="button"
              onClick={() => onDismiss(item.id)}
              className="-m-1 rounded-md p-1 text-ink-subtle hover:bg-surface-muted hover:text-ink focus-visible:outline-2 focus-visible:outline-focus"
              aria-label={closeLabel}
            >
              <IconX className="size-4" aria-hidden />
            </button>
          </div>
        );
      })}
    </div>
  );
  // Fixed positioning inside the dialog still refers to the viewport (the
  // dialog has no transform), so the corner does not move.
  return topDialog ? createPortal(viewport, topDialog) : viewport;
}

export function useToast(): ToastApi {
  const toast = useContext(ToastContext);
  if (!toast) {
    throw new Error("useToast() must be used inside <ToastProvider>.");
  }
  return toast;
}
