"use client";

/**
 * A panel over the page that suits the screen: on phones it rises from
 * the bottom (a sheet with a grab handle, at most 88 % of the screen, the
 * thumb's reach), on large screens it slides from the end edge like a
 * Drawer. A modal native <dialog> with the contract of Modal and Drawer:
 * focus stays inside, Escape and a press on the backdrop close it,
 * `onClose` runs only when the person closes it, and the content stays
 * while it slides out.
 *
 *     <Sheet open={isOpen} onClose={() => setOpen(false)} title="Filters" footer={<Button>Show</Button>}>
 *       …fields…
 *     </Sheet>
 */

import { useId, type ReactNode } from "react";

import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";

import { IconX } from "../icons";
import { useClosingContent } from "./useClosingContent";
import { useModalDialog } from "./useModalDialog";

export function Sheet({
  open,
  onClose,
  title,
  description,
  footer,
  className,
  children,
}: {
  open: boolean;
  onClose: () => void;
  title: ReactNode;
  description?: ReactNode;
  footer?: ReactNode;
  className?: string;
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
      data-motion="sheet"
      aria-labelledby={titleId}
      aria-describedby={shownDescription ? descriptionId : undefined}
      className={cn(
        "fixed inset-x-0 top-auto bottom-0 m-0 max-h-[88dvh] w-full max-w-none overflow-hidden rounded-t-3xl border-t border-line bg-surface p-0 text-ink shadow-2xl",
        "lg:start-auto lg:top-0 lg:h-dvh lg:max-h-dvh lg:w-[28rem] lg:rounded-none lg:border-t-0 lg:border-s",
        className,
      )}
    >
      {closing.isMounted ? (
        <div className="flex max-h-[88dvh] flex-col lg:h-full lg:max-h-none">
          <div aria-hidden className="mx-auto mt-2.5 h-1.5 w-10 shrink-0 rounded-full bg-line-strong/60 lg:hidden" />
          <header className="flex shrink-0 items-start justify-between gap-4 px-5 pt-2 pb-3 lg:border-b lg:border-line lg:py-4">
            <div className="min-w-0 space-y-1">
              <h2 id={titleId} className="text-lg font-semibold tracking-tight lg:text-base">
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
              aria-label={t("common.close")}
              className="motion-press -me-2 flex size-11 shrink-0 cursor-pointer items-center justify-center rounded-full text-ink-muted hover:bg-surface-muted hover:text-ink lg:-m-1 lg:size-8 lg:rounded-md"
            >
              <IconX className="size-5" aria-hidden />
            </button>
          </header>
          <div className="min-h-0 flex-1 overflow-y-auto px-5 pb-5 lg:pt-5">{shownChildren}</div>
          {shownFooter ? (
            <footer className="flex shrink-0 flex-wrap items-center justify-end gap-3 border-t border-line px-5 pt-3.5 pb-[calc(0.875rem+env(safe-area-inset-bottom))] lg:pb-3.5">
              {shownFooter}
            </footer>
          ) : null}
        </div>
      ) : null}
    </dialog>
  );
}
