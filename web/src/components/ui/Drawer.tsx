"use client";

/**
 * A side panel over the page (a modal native <dialog>): for secondary
 * content that would crowd a form, such as a checklist or details. It slides
 * from the end edge (right in left-to-right languages) and fills the screen
 * on phones. Same contract as Modal: `onClose` runs only when the person
 * closes it; it slides in with a spring and keeps its content while it
 * slides out.
 *
 *     <Drawer open={isOpen} onClose={() => setOpen(false)} title="What to add">
 *       …list…
 *     </Drawer>
 */

import { useId, type ReactNode } from "react";

import { useI18n } from "@/i18n/client";

import { IconX } from "../icons";
import { useClosingContent } from "./useClosingContent";
import { useModalDialog } from "./useModalDialog";

export function Drawer({
  open,
  onClose,
  title,
  description,
  footer,
  children,
}: {
  open: boolean;
  onClose: () => void;
  title: ReactNode;
  description?: ReactNode;
  footer?: ReactNode;
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
      data-motion="drawer-end"
      aria-labelledby={titleId}
      aria-describedby={shownDescription ? descriptionId : undefined}
      className="ms-auto me-0 my-0 h-dvh max-h-dvh w-full max-w-none overflow-hidden border-s border-line bg-surface p-0 text-ink shadow-2xl sm:w-[28rem]"
    >
      {closing.isMounted ? (
        <div className="flex h-full flex-col">
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
