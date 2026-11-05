import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

export interface Fact {
  label: ReactNode;
  value: ReactNode;
  /** Spans the whole row (long values). */
  wide?: boolean;
}

/** Label/value pairs in a responsive grid (a <dl>). */
export function Facts({ items, columns = 2, className }: { items: readonly (Fact | null | false)[]; columns?: 2 | 3 | 4; className?: string }) {
  const visible = items.filter((item): item is Fact => Boolean(item));
  return (
    <dl
      className={cn(
        "grid gap-x-6 gap-y-4 text-sm sm:grid-cols-2",
        columns >= 3 && "lg:grid-cols-3",
        columns === 4 && "xl:grid-cols-4",
        className,
      )}
    >
      {visible.map((item, index) => (
        <div key={index} className={cn("min-w-0", item.wide && "sm:col-span-full")}>
          <dt className="text-ink-subtle">{item.label}</dt>
          <dd className="mt-0.5 font-medium break-words text-ink">{item.value}</dd>
        </div>
      ))}
    </dl>
  );
}
