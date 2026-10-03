"use client";

/**
 * A modal dialog on the native <dialog> element: focus is trapped, Escape
 * closes it and the page behind is inert. `onClose` is called only when the
 * person closes it (Escape, the close button, the backdrop), never when
 * `open` turns false, so one dialog can replace another safely.
 *
 *     <Modal open={isOpen} onClose={() => setOpen(false)} title="New business"
 *            footer={<Button onClick={save}>Save</Button>}>
 *       …form…
 *     </Modal>
 *
 * It springs in and fades out (`data-motion`, src/styles/motion.css); while
 * it fades out it keeps showing what it showed when it was open.
 */

import { useId, type ReactNode } from "react";

import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";

import { IconX } from "../icons";
import { useClosingContent } from "./useClosingContent";
import { useModalDialog } from "./useModalDialog";

const SIZES = { sm: "max-w-md", md: "max-w-lg", lg: "max-w-2xl", xl: "max-w-4xl" } as const;

export function Modal({
  open,
  onClose,
  title,
  description,
  footer,
  size = "md",
  children,
}: {
  open: boolean;
  onClose: () => void;
  title: ReactNode;
  description?: ReactNode;
  footer?: ReactNode;
  size?: keyof typeof SIZES;
  children: ReactNode;
}) {
  const { t } = useI18n();
  const dialog = useModalDialog(open, onClose);
  const titleId = useId();
  const descriptionId = useId();
  const closing = useClosingContent(open, [title, description, footer, children] as const);
  const [shownTitle, shownDescription, shownFooter, shownChildren] = closing.content;

  return (
    <dialog
      {...dialog}
      data-motion="modal"
      aria-labelledby={titleId}
      aria-describedby={shownDescription ? descriptionId : undefined}
      className={cn(
        "m-auto max-h-[calc(100dvh-2rem)] w-[calc(100%-2rem)] overflow-hidden rounded-2xl border border-line bg-surface p-0 text-ink shadow-2xl",
        SIZES[size],
      )}
    >
      {closing.isMounted ? (
        <div className="flex max-h-[calc(100dvh-2rem)] flex-col">
          <header className="flex items-start justify-between gap-4 border-b border-line px-5 py-4">
            <div className="min-w-0 space-y-1">
              <h2 id={titleId} className="text-base font-semibold tracking-tight">
                {shownTitle}
              </h2>
              {shownDescription ? (
                <p id={descriptionId} className="text-sm text-ink-muted">
                  {shownDescription}
                </p>
              ) : null}
            </div>
            <button
              type="button"
              onClick={onClose}
              className="motion-press -m-1 rounded-md p-1 text-ink-subtle hover:bg-surface-muted hover:text-ink"
              aria-label={t("common.close")}
            >
              <IconX className="size-5" aria-hidden />
            </button>
          </header>
          <div className="min-h-0 flex-1 overflow-y-auto p-5">{shownChildren}</div>
          {shownFooter ? (
            <footer className="flex flex-wrap items-center justify-end gap-3 border-t border-line px-5 py-3.5">
              {shownFooter}
            </footer>
          ) : null}
        </div>
      ) : null}
    </dialog>
  );
}
