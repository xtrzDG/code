"use client";

import { createContext, useContext, type ReactNode } from "react";

import { cn } from "@/lib/cn";

/** 1 on a page of its own; 2 inside a section frame, which owns the page's <h1>. */
type PageLevel = 1 | 2;

const PageLevelContext = createContext<PageLevel>(1);

/**
 * The pages of a section frame (Messages, Assistant, Settings): the frame
 * shows the section's <h1> and tabs, so each page's PageHeader inside
 * becomes an <h2> for screen readers, and shows only its description and
 * actions.
 */
export function SubPages({ children }: { children: ReactNode }) {
  return <PageLevelContext.Provider value={2}>{children}</PageLevelContext.Provider>;
}

/** Whether this part of the page is inside a section frame. */
export function usePageLevel(): PageLevel {
  return useContext(PageLevelContext);
}

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
  const level = usePageLevel();

  if (level === 2) {
    const hasText = Boolean(eyebrow || description);
    if (!hasText && !actions) {
      return <h2 className="sr-only">{title}</h2>;
    }
    return (
      <header className={cn("mb-5 flex flex-wrap items-center justify-between gap-x-4 gap-y-3", className)}>
        <h2 className="sr-only">{title}</h2>
        {hasText ? (
          <div className="min-w-0 space-y-1">
            {eyebrow ? <p className="text-sm font-medium text-accent">{eyebrow}</p> : null}
            {description ? <p className="max-w-3xl text-sm text-ink-muted">{description}</p> : null}
          </div>
        ) : null}
        {actions ? <div className="ms-auto flex max-w-full min-w-0 flex-wrap items-center gap-2">{actions}</div> : null}
      </header>
    );
  }

  return (
    <header className={cn("mb-6 flex flex-wrap items-end justify-between gap-4 sm:mb-8", className)}>
      <div className="min-w-0 space-y-1.5">
        {eyebrow ? <p className="text-sm font-medium text-accent">{eyebrow}</p> : null}
        <h1 className="text-xl font-semibold tracking-tight text-ink sm:text-2xl">{title}</h1>
        {description ? <p className="max-w-3xl text-sm text-ink-muted">{description}</p> : null}
      </div>
      {actions ? <div className="flex max-w-full min-w-0 flex-wrap items-center gap-2">{actions}</div> : null}
    </header>
  );
}
