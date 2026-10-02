import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

/** What to show when a list is empty or a section is not ready yet. */
export function EmptyState({
  icon,
  title,
  description,
  action,
  className,
}: {
  icon?: ReactNode;
  title: ReactNode;
  description?: ReactNode;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("flex flex-col items-center px-6 py-12 text-center", className)}>
      {icon ? (
        <div className="mb-4 flex size-11 items-center justify-center rounded-xl border border-line bg-surface-muted text-ink-muted" aria-hidden>
          {icon}
        </div>
      ) : null}
      <h3 className="text-[0.9375rem] font-semibold text-ink">{title}</h3>
      {description ? <p className="mt-1.5 max-w-md text-sm text-ink-muted">{description}</p> : null}
      {action ? <div className="mt-6">{action}</div> : null}
    </div>
  );
}
