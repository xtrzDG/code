"use client";

/**
 * A side panel over the page (a modal native <dialog>): for secondary
 * content that would crowd a form, such as a checklist or details. It slides
 * from the end edge (right in left-to-right languages) and fills the screen
 * on phones. Same contract as Modal: `onClose` runs only when the person
 * closes it.
 *
 *     <Drawer open={isOpen} onClose={() => setOpen(false)} title="What to add">
 *       …list…
 *     </Drawer>
 */

import { useId, type ReactNode } from "react";

import { useI18n } from "@/i18n/client";

import { IconX } from "../icons";
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

  return (
    <dialog
      {...dialog}
      aria-labelledby={titleId}
      aria-describedby={description ? descriptionId : undefined}
      className="ms-auto me-0 my-0 h-dvh max-h-dvh w-full max-w-none overflow-hidden border-s border-line bg-surface p-0 text-ink shadow-2xl sm:w-[28rem]"
    >
      {open ? (
        <div className="flex h-full flex-col">
          <header className="flex items-start justify-between gap-4 border-b border-line px-5 py-4 sm:px-6">
            <div className="min-w-0 space-y-1">
              <h2 id={titleId} className="text-lg font-semibold">
                {title}
              </h2>
              {description ? (
                <p id={descriptionId} className="text-sm text-ink-muted">
                  {description}
                </p>
              ) : null}
            </div>
            <button
              type="button"
              onClick={onClose}
              className="-m-1 rounded-md p-1 text-ink-subtle hover:bg-surface-muted hover:text-ink"
              aria-label={t("common.close")}
            >
              <IconX className="size-5" aria-hidden />
            </button>
          </header>
          <div className="min-h-0 flex-1 overflow-y-auto px-5 py-5 sm:px-6">{children}</div>
          {footer ? (
            <footer className="flex flex-wrap items-center justify-end gap-3 border-t border-line px-5 py-4 sm:px-6">
              {footer}
            </footer>
          ) : null}
        </div>
      ) : null}
    </dialog>
  );
}
