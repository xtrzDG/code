"use client";

import { LayoutGroup } from "motion/react";
import * as m from "motion/react-m";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useId, type ReactNode } from "react";

import { usePageLevel } from "@/components/ui";
import { cn } from "@/lib/cn";
import { springTransition } from "@/lib/motion";

export interface SectionTab {
  href: string;
  label: ReactNode;
  /** Active only on this exact path (the section's first tab). */
  exact?: boolean;
  /** Drawn apart at the end of the row (the Assistant's "Advanced"). */
  isApart?: boolean;
  /** Its full name when the label is shorter (a tooltip and for screen readers). */
  title?: string;
}

/**
 * Sub-pages of a section as a row of links (scrolls sideways on phones);
 * the current one is marked with aria-current="page" and an underline
 * that glides between tabs. Inside a section frame (a page's own sub-pages,
 * like Knowledge inside Assistant) the row turns into quieter pills.
 * `activeHref` names the current tab when the address alone cannot (the
 * conversations tab is current on /messages/{id} but not on /messages/leads).
 */
export function SectionTabs({
  label,
  tabs,
  activeHref,
  className,
}: {
  label: string;
  tabs: readonly SectionTab[];
  activeHref?: string;
  className?: string;
}) {
  const pathname = usePathname();
  const groupId = useId();
  const isNested = usePageLevel() === 2;
  const isActive = (tab: SectionTab) =>
    activeHref !== undefined
      ? tab.href === activeHref
      : tab.exact
        ? pathname === tab.href
        : pathname === tab.href || pathname.startsWith(`${tab.href}/`);

  return (
    <LayoutGroup id={groupId}>
      <nav aria-label={label} className={cn("-mx-4 mb-6 overflow-x-auto px-4 sm:mx-0 sm:px-0", className)}>
        <ul className={cn("flex min-w-max items-center gap-1", !isNested && "border-b border-line")}>
          {tabs.map((tab) => {
            const active = isActive(tab);
            return (
              <li key={tab.href} className={cn(tab.isApart && "ms-auto flex items-center gap-1 ps-3")}>
                {tab.isApart ? <span aria-hidden className="me-1 h-5 w-px bg-line" /> : null}
                <Link
                  href={tab.href}
                  aria-current={active ? "page" : undefined}
                  title={tab.title}
                  className={cn(
                    "relative inline-flex items-center gap-2 text-sm font-medium whitespace-nowrap transition-colors",
                    "focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-focus",
                    isNested
                      ? "h-9 rounded-full px-3.5 pointer-coarse:h-11"
                      : "-mb-px h-11 px-3",
                    active ? (isNested ? "text-accent-ink" : "text-accent") : "text-ink-muted hover:text-ink",
                    !active && isNested && "hover:bg-surface-muted",
                  )}
                >
                  {active ? (
                    <m.span
                      layoutId="section-tab"
                      transition={springTransition("snappy")}
                      aria-hidden
                      className={cn(
                        "absolute",
                        isNested ? "inset-0 rounded-full bg-accent-soft" : "inset-x-0 -bottom-px h-0.5 rounded-full bg-accent-solid",
                      )}
                    />
                  ) : null}
                  <span className="relative inline-flex items-center gap-2">{tab.label}</span>
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>
    </LayoutGroup>
  );
}
