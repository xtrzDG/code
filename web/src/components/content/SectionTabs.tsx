"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

export interface SectionTab {
  href: string;
  label: ReactNode;
  /** Active only on this exact path (the section's first tab). */
  exact?: boolean;
}

/**
 * Sub-pages of a section as a row of links (scrolls sideways on phones);
 * the current one is marked with aria-current="page".
 */
export function SectionTabs({ label, tabs, className }: { label: string; tabs: readonly SectionTab[]; className?: string }) {
  const pathname = usePathname();
  const isActive = (tab: SectionTab) =>
    tab.exact ? pathname === tab.href : pathname === tab.href || pathname.startsWith(`${tab.href}/`);

  return (
    <nav aria-label={label} className={cn("-mx-4 mb-6 overflow-x-auto px-4 sm:mx-0 sm:px-0", className)}>
      <ul className="flex min-w-max gap-1 border-b border-line">
        {tabs.map((tab) => {
          const active = isActive(tab);
          return (
            <li key={tab.href}>
              <Link
                href={tab.href}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "-mb-px inline-flex h-11 items-center border-b-2 px-3 text-sm font-medium whitespace-nowrap transition-colors",
                  "focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-focus",
                  active ? "border-accent-solid text-accent" : "border-transparent text-ink-muted hover:border-line-strong hover:text-ink",
                )}
              >
                {tab.label}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
