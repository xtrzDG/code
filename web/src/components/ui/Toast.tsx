"use client";

/**
 * Short notifications in the corner of the screen.
 *
 *     const toast = useToast();
 *     toast.success(t("common.saved"));
 *     toast.error(apiError);                      // localized by error code
 *     toast.error(apiError, { conflict: "bookings.slotTaken" });
 *     toast.undoable(t("leads.updated", …), () => setStatus.run(lead, previous));
 *     toast.success({ text: t("inbox.assign.assigned"), values: { name } }); // a name is user content
 *
 * An undoable toast carries an Undo button for 5 seconds (the window runs
 * down under it and stops while the pointer or the keyboard focus is on
 * the toast). Other toasts keep their time. While a modal <dialog> is open everything outside it is inert
 * and drawn below it, so the toasts move into the topmost open dialog.
 */

import { createContext, useCallback, useContext, useMemo, useRef, useState, type ReactNode } from "react";

import { describeError, type ErrorMessageOverrides, type ReasonMessages } from "@/api/errors";
import { useI18n } from "@/i18n/client";

import { ToastViewport, type ToastItem, type ToastTitle, type ToastTone } from "./ToastViewport";

export type { ToastTitle } from "./ToastViewport";

/** How long Undo is offered after an action. */
export const UNDO_WINDOW_MS = 5_000;

interface ToastAction {
  label: string;
  onAction: () => void;
}

export interface ToastApi {
  show: (toast: {
    tone: ToastTone;
    title: ToastTitle;
    description?: string | null;
    durationMs?: number;
    /** A button in the toast (Undo); pressing it closes the toast. */
    action?: ToastAction;
  }) => void;
  success: (title: ToastTitle, description?: string) => void;
  info: (title: ToastTitle, description?: string) => void;
  /** A success with an Undo button for UNDO_WINDOW_MS. */
  undoable: (title: ToastTitle, onUndo: () => void) => void;
  /** An ApiError (or anything thrown) as a localized message; known refusal reasons get their own text. */
  error: (error: unknown, overrides?: ErrorMessageOverrides, reasonMessages?: ReasonMessages) => void;
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

  const show = useCallback<ToastApi["show"]>(({ tone, title, description, durationMs, action }) => {
    const id = nextId.current++;
    const duration = durationMs ?? (action ? UNDO_WINDOW_MS : tone === "error" ? ERROR_DURATION_MS : DEFAULT_DURATION_MS);
    setItems((current) => [...current, { id, tone, title, description, action, durationMs: duration }].slice(-MAX_VISIBLE));
  }, []);

  const api = useMemo<ToastApi>(
    () => ({
      show,
      dismiss,
      success: (title, description) => show({ tone: "success", title, description }),
      info: (title, description) => show({ tone: "info", title, description }),
      undoable: (title, onUndo) => show({ tone: "success", title, action: { label: t("common.undo"), onAction: onUndo } }),
      error: (error, overrides, reasonMessages) => {
        const { title, detail, requestId } = describeError(error, t, overrides, reasonMessages);
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

export function useToast(): ToastApi {
  const toast = useContext(ToastContext);
  if (!toast) {
    throw new Error("useToast() must be used inside <ToastProvider>.");
  }
  return toast;
}
