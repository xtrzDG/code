"use client";

/**
 * The navigation column of the signed-in cabinet (the sidebar on large
 * screens, the slide-in menu on phones): brand, the business switcher, the
 * sections and, at the bottom, who is signed in.
 */

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ComponentType, ReactNode } from "react";

import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";
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
}

export function isActiveItem(pathname: string, href: string): boolean {
  return pathname === href || pathname.startsWith(`${href}/`);
}

function NavList({ items, onNavigate }: { items: readonly ShellNavItem[]; onNavigate?: () => void }) {
  const pathname = usePathname();
  const { t } = useI18n();
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
          aria-current={active ? "page" : undefined}
          className={cn(
            "flex h-9 items-center gap-3 rounded-lg px-2.5 text-sm transition-colors",
            active
              ? "bg-surface-muted font-medium text-ink ring-1 ring-line ring-inset"
              : "text-ink-muted hover:bg-surface-muted/60 hover:text-ink",
          )}
        >
          <Icon className={cn("size-[1.125rem] shrink-0", active ? "text-accent" : "text-ink-subtle")} aria-hidden />
          <span className="truncate">{item.label}</span>
        </Link>
      </li>
    );
  };

  return (
    <nav aria-label={t("nav.mainNavigation")}>
      <ul className="space-y-0.5">{primary.map(renderItem)}</ul>
      {secondary.length > 0 ? (
        <ul className="mt-4 space-y-0.5 border-t border-line pt-4">{secondary.map(renderItem)}</ul>
      ) : null}
    </nav>
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
      <Brand href={HOME_PATH} className="px-1.5 py-1" />
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
