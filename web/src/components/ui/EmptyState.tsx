import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

/**
 * What to show when a list is empty or a section is not ready yet: a small
 * icon in a tile, or for the cabinet's calm moments (an empty inbox, the
 * first day, no bookings, no invoices) a spot illustration from
 * @/components/illustrations, which settles in when it appears.
 */
export function EmptyState({
  icon,
  illustration,
  title,
  description,
  action,
  className,
}: {
  icon?: ReactNode;
  /** A spot illustration, shown instead of the icon. */
  illustration?: ReactNode;
  title: ReactNode;
  description?: ReactNode;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("flex flex-col items-center px-6 py-12 text-center", className)}>
      {illustration ? (
        <div className="mb-5 w-36 animate-settle sm:w-44" aria-hidden>
          {illustration}
        </div>
      ) : icon ? (
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
