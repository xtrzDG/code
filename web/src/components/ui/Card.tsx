import type { ComponentPropsWithRef, ReactNode } from "react";

import { cn } from "@/lib/cn";

/**
 * A surface for a block of content, with an optional header and footer.
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
}) {
  const hasHeader = title !== undefined || description !== undefined || actions !== undefined;
  return (
    <section className={cn("rounded-2xl border border-line bg-surface shadow-sm", className)} {...props}>
      {hasHeader ? (
        <header className="flex flex-wrap items-start justify-between gap-3 border-b border-line px-5 py-4 sm:px-6">
          <div className="min-w-0 space-y-1">
            {title !== undefined ? <h2 className="text-base font-semibold text-ink">{title}</h2> : null}
            {description !== undefined ? <p className="text-sm text-ink-muted">{description}</p> : null}
          </div>
          {actions !== undefined ? <div className="flex shrink-0 items-center gap-2">{actions}</div> : null}
        </header>
      ) : null}
      <div className={cn(padded && "px-5 py-5 sm:px-6")}>{children}</div>
      {footer !== undefined ? (
        <footer className="flex flex-wrap items-center justify-end gap-3 border-t border-line px-5 py-4 sm:px-6">
          {footer}
        </footer>
      ) : null}
    </section>
  );
}
