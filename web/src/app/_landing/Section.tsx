import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

/** One block of the landing page: a hairline on top, a heading and a short lead. */
export function Section({
  id,
  title,
  subtitle,
  children,
  className,
}: {
  id: string;
  title: string;
  subtitle?: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section id={id} aria-labelledby={`${id}-title`} className={cn("scroll-mt-16 border-t border-line py-16 sm:py-24", className)}>
      <div className="mx-auto w-full max-w-6xl px-4 sm:px-6">
        <div className="mb-10 max-w-2xl space-y-3 sm:mb-14">
          <h2 id={`${id}-title`} className="text-2xl font-semibold tracking-tight text-balance text-ink sm:text-3xl">
            {title}
          </h2>
          {subtitle ? <p className="text-base text-pretty text-ink-muted">{subtitle}</p> : null}
        </div>
        {children}
      </div>
    </section>
  );
}

/** A small square with an icon, for feature and channel lists. */
export function IconTile({ children }: { children: ReactNode }) {
  return (
    <span
      className="flex size-9 shrink-0 items-center justify-center rounded-lg border border-line bg-surface-muted text-accent"
      aria-hidden
    >
      {children}
    </span>
  );
}
