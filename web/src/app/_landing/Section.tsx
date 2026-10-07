import type { ReactNode } from "react";

import { Parallax, Reveal } from "@/components/motion";
import { cn } from "@/lib/cn";

/**
 * One block of the landing page: a hairline on top, a heading and a short
 * lead that rise in when the block scrolls into view, and optionally a
 * coloured glow drifting behind it slower than the page (a depth layer).
 * Rendered by the browser only near the screen (`landing-deferred`), so the
 * first frame is the hero's alone.
 */
export function Section({
  id,
  title,
  subtitle,
  glow,
  layout = "stacked",
  children,
  className,
}: {
  id: string;
  title: string;
  subtitle?: string;
  /** Where the background glow sits. */
  glow?: "left" | "right";
  /** "split": the heading beside the content on wide screens (a showcase). */
  layout?: "stacked" | "split";
  children: ReactNode;
  className?: string;
}) {
  const isSplit = layout === "split";
  return (
    <section
      id={id}
      aria-labelledby={`${id}-title`}
      className={cn("landing-deferred relative isolate scroll-mt-16 overflow-x-clip border-t border-line py-16 sm:py-24", className)}
    >
      {glow ? (
        <Parallax
          speed={-0.6}
          className={cn(
            "pointer-events-none absolute top-1/4 -z-10 size-[28rem] rounded-full opacity-70",
            "bg-[radial-gradient(circle,color-mix(in_oklab,var(--accent-solid)_28%,transparent),transparent_70%)]",
            glow === "left" ? "-start-40" : "-end-40",
          )}
        />
      ) : null}
      <div
        className={cn(
          "mx-auto w-full max-w-6xl px-4 sm:px-6",
          isSplit && "lg:grid lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1fr)] lg:items-center lg:gap-16",
        )}
      >
        <Reveal className={cn("mb-10 max-w-2xl space-y-3 sm:mb-14", isSplit && "lg:mb-0")}>
          <h2 id={`${id}-title`} className="text-2xl font-semibold tracking-tight text-balance text-ink sm:text-3xl">
            {title}
          </h2>
          {subtitle ? <p className="text-base text-pretty text-ink-muted">{subtitle}</p> : null}
        </Reveal>
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
