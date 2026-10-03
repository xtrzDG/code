"use client";

/**
 * The cabinet's side column on large screens: the mark, the business
 * switcher, the sections (or, before the assistant exists, the one big
 * "Create an AI assistant" entry) and the user menu at the bottom. It
 * collapses to a rail of icons; the choice is kept in a cookie.
 */

import type { ReactNode } from "react";

import type { CurrentUserView } from "@/api/types";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";
import { HOME_PATH } from "@/lib/navigation";

import { IconChevronRight } from "../icons";
import { Brand } from "./Brand";
import { SidebarNav } from "./SidebarNav";
import type { ShellNavItem } from "./types";
import { UserMenu } from "./UserMenu";

export function Sidebar({
  items,
  top,
  replacement,
  me,
  collapsed,
  onToggleCollapsed,
}: {
  items: readonly ShellNavItem[];
  /** Above the navigation (the business switcher). */
  top?: ReactNode;
  /** Instead of the navigation (the setup entry before the assistant exists). */
  replacement?: (collapsed: boolean) => ReactNode;
  me: CurrentUserView;
  collapsed: boolean;
  onToggleCollapsed: () => void;
}) {
  const { t } = useI18n();
  return (
    <div className="flex h-full flex-col">
      <div className={cn("flex items-center gap-2 pt-4 pb-3", collapsed ? "flex-col px-2" : "justify-between px-3")}>
        <Brand href={HOME_PATH} hideName={collapsed} className="px-1.5 py-1" />
        <button
          type="button"
          onClick={onToggleCollapsed}
          aria-label={collapsed ? t("navigation.expand") : t("navigation.collapse")}
          aria-expanded={!collapsed}
          title={collapsed ? t("navigation.expand") : t("navigation.collapse")}
          className="flex size-8 cursor-pointer items-center justify-center rounded-lg text-ink-subtle transition-colors hover:bg-surface-muted hover:text-ink"
        >
          <IconChevronRight
            className={cn("size-4 transition-transform duration-(--motion-base) rtl:-scale-x-100", !collapsed && "rotate-180 rtl:rotate-0")}
            aria-hidden
          />
        </button>
      </div>
      {top ? <div className={cn(collapsed ? "px-2" : "px-3")}>{top}</div> : null}
      <div className={cn("min-h-0 flex-1 overflow-x-hidden overflow-y-auto py-4", collapsed ? "px-2" : "px-3")}>
        {replacement ? replacement(collapsed) : <SidebarNav items={items} collapsed={collapsed} />}
      </div>
      <div className={cn("border-t border-line py-3", collapsed ? "px-2" : "px-3")}>
        <UserMenu me={me} collapsed={collapsed} />
      </div>
    </div>
  );
}
