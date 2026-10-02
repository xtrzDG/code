"use client";

/**
 * The navigation column of the signed-in cabinet (the sidebar on large
 * screens, the slide-in menu on phones): brand, the business switcher, the
 * sections and, at the bottom, who is signed in.
 */

import { LayoutGroup } from "motion/react";
import * as m from "motion/react-m";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useId, type ComponentType, type ReactNode } from "react";

import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";
import { springTransition } from "@/lib/motion";
import { HOME_PATH } from "@/lib/navigation";

import type { IconProps } from "../icons";
import { Brand } from "./Brand";
import { SignOutButton } from "./SignOutButton";

export interface ShellNavItem {
  href: string;
  label: string;
  icon: ComponentType<IconProps>;
  /** Shown after the main list, separated (e.g. platform admin). */
  secondary?: boolean;
  /** Loads the section's first data when the pointer or the focus reaches the link. */
  onPrefetch?: () => void;
}

export function isActiveItem(pathname: string, href: string): boolean {
  return pathname === href || pathname.startsWith(`${href}/`);
}

function NavList({ items, onNavigate }: { items: readonly ShellNavItem[]; onNavigate?: () => void }) {
  const pathname = usePathname();
  const { t } = useI18n();
  const groupId = useId();
  const primary = items.filter((item) => !item.secondary);
  const secondary = items.filter((item) => item.secondary);

  const renderItem = (item: ShellNavItem) => {
    const active = isActiveItem(pathname, item.href);
    const Icon = item.icon;
    return (
      <li key={item.href}>
        <Link
          href={item.href}
          onClick={onNavigate}
          onPointerEnter={active ? undefined : item.onPrefetch}
          onFocus={active ? undefined : item.onPrefetch}
          aria-current={active ? "page" : undefined}
          className={cn(
            "relative flex h-10 items-center gap-3 rounded-lg px-2.5 text-sm transition-colors lg:h-9",
            active ? "font-medium text-ink" : "text-ink-muted hover:bg-surface-muted/60 hover:text-ink",
          )}
        >
          {active ? (
            // The marker glides from the old section to the new one (a shared layout animation).
            <m.span
              layoutId="active-section"
              transition={springTransition("layout")}
              className="absolute inset-0 rounded-lg bg-surface-muted ring-1 ring-line ring-inset"
              aria-hidden
            />
          ) : null}
          <Icon className={cn("relative size-[1.125rem] shrink-0", active ? "text-accent" : "text-ink-subtle")} aria-hidden />
          <span className="relative truncate">{item.label}</span>
        </Link>
      </li>
    );
  };

  return (
    // Its own group: the sidebar and the phone menu each move their own marker.
    <LayoutGroup id={groupId}>
      <nav aria-label={t("nav.mainNavigation")}>
        <ul className="space-y-0.5">{primary.map(renderItem)}</ul>
        {secondary.length > 0 ? (
          <ul className="mt-4 space-y-0.5 border-t border-line pt-4">{secondary.map(renderItem)}</ul>
        ) : null}
      </nav>
    </LayoutGroup>
  );
}

export function SidebarContent({
  items,
  top,
  userName,
  onNavigate,
}: {
  items: readonly ShellNavItem[];
  top?: ReactNode;
  userName: string;
  onNavigate?: () => void;
}) {
  const { t } = useI18n();
  return (
    <div className="flex h-full flex-col gap-5 overflow-y-auto px-3 py-4">
      {/* In the phone menu the close button sits at the end of this row. */}
      <Brand href={HOME_PATH} className={cn("px-1.5 py-1", onNavigate && "mr-9")} />
      {top}
      <div className="flex-1">
        <NavList items={items} onNavigate={onNavigate} />
      </div>
      <div className="space-y-1 border-t border-line pt-3">
        <p className="truncate px-2.5 text-xs text-ink-subtle" title={userName}>
          {t("shell.signedInAs", { name: userName })}
        </p>
        <SignOutButton className="w-full" />
      </div>
    </div>
  );
}
