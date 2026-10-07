import type { ComponentPropsWithRef, ReactNode } from "react";

import { cn } from "@/lib/cn";

/**
 * A surface for a block of content, with an optional header and footer.
 * `interactive` (a card that is itself a link or opens something) lifts it
 * a little under the pointer. Its header and title are marked
 * (`data-card-header`, `data-card-title`), so a wrapper that already names
 * the card (a phone's folded row on the Overview) can hide them.
 *
 *     <Card title="Opening hours" description="..." actions={<Button>…</Button>}>
 *       …
 *     </Card>
 */
export function Card({
  title,
  description,
  actions,
  footer,
  padded = true,
  interactive = false,
  className,
  children,
  ...props
}: Omit<ComponentPropsWithRef<"section">, "title"> & {
  title?: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
  footer?: ReactNode;
  /** False for edge-to-edge content such as tables. */
  padded?: boolean;
  interactive?: boolean;
}) {
  const hasHeader = title !== undefined || description !== undefined || actions !== undefined;
  return (
    // min-w-0: in a grid or a row a card shrinks with the screen instead of
    // widening it to its longest text (Georgian and Russian run long).
    <section className={cn("min-w-0 rounded-2xl border border-line bg-surface", interactive && "motion-lift", className)} {...props}>
      {hasHeader ? (
        <header
          data-card-header=""
          data-title-only={description === undefined && actions === undefined ? "" : undefined}
          className="flex flex-wrap items-start justify-between gap-3 border-b border-line px-5 py-4"
        >
          <div className="min-w-0 space-y-1">
            {title !== undefined ? (
              <h2 data-card-title="" className="text-[0.9375rem] font-semibold tracking-tight text-ink">
                {title}
              </h2>
            ) : null}
            {description !== undefined ? <p className="text-sm text-ink-muted">{description}</p> : null}
          </div>
          {actions !== undefined ? <div className="flex max-w-full min-w-0 flex-wrap items-center gap-2">{actions}</div> : null}
        </header>
      ) : null}
      <div className={cn(padded && "p-5")}>{children}</div>
      {footer !== undefined ? (
        <footer className="flex flex-wrap items-center justify-end gap-3 border-t border-line px-5 py-3.5">
          {footer}
        </footer>
      ) : null}
    </section>
  );
}
