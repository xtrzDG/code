import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

/** The title row of a page: one <h1>, a description and page actions. */
export function PageHeader({
  title,
  description,
  actions,
  eyebrow,
  className,
}: {
  title: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
  /** Small text above the title (a business name, a step number). */
  eyebrow?: ReactNode;
  className?: string;
}) {
  return (
    <header className={cn("mb-6 flex flex-wrap items-end justify-between gap-4 sm:mb-8", className)}>
      <div className="min-w-0 space-y-1.5">
        {eyebrow ? <p className="text-sm font-medium text-accent">{eyebrow}</p> : null}
        <h1 className="text-2xl font-semibold tracking-tight text-ink sm:text-3xl">{title}</h1>
        {description ? <p className="max-w-3xl text-sm text-ink-muted sm:text-base">{description}</p> : null}
      </div>
      {actions ? <div className="flex flex-wrap items-center gap-2">{actions}</div> : null}
    </header>
  );
}
