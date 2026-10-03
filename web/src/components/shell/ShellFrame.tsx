"use client";

/**
 * Page frame of the signed-in cabinet. Large screens: the sidebar
 * (collapsible to icons) and the page. Phones: a calm top bar, the page and
 * the bottom tab bar with "More". The navigation is passed in by
 * BusinessShell (business pages) or AdminShell (platform admin).
 */

import { useState, type CSSProperties, type ReactNode } from "react";

import type { CurrentUserView } from "@/api/types";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";
import { sidebarCookie } from "@/lib/shellPreferences";

import { MoreSheet } from "./MoreSheet";
import { PhoneTabBar } from "./PhoneTabBar";
import { PhoneTopBar } from "./PhoneTopBar";
import { ServiceWorker } from "./ServiceWorker";
import { Sidebar } from "./Sidebar";
import type { ShellNavItem } from "./types";
import { UserAvatar } from "./UserAvatar";

export function ShellFrame({
  items,
  switcher,
  sidebarReplacement,
  title,
  context,
  me,
  initialCollapsed,
  showTabBar = true,
  showPhoneTopBar = true,
  isWide = false,
  children,
}: {
  items: readonly ShellNavItem[];
  /** The business switcher, in the sidebar and in "More" (closes "More" once used). */
  switcher?: (onNavigate?: () => void, compact?: boolean) => ReactNode;
  /** Instead of the sections in the sidebar (the setup entry), for the expanded or collapsed sidebar. */
  sidebarReplacement?: (collapsed: boolean) => ReactNode;
  /** Where you are, for the phone's top bar. */
  title?: string;
  /** The business name (or "Platform admin"), above the title on phones. */
  context?: string;
  me: CurrentUserView;
  initialCollapsed: boolean;
  /** False before the assistant exists and on an open conversation (its reply box needs the space). */
  showTabBar?: boolean;
  /** False on an open conversation: its own bar (back, customer, actions) is the top of the phone screen. */
  showPhoneTopBar?: boolean;
  /** The page uses the full width of large screens (the inbox: a list beside a conversation). */
  isWide?: boolean;
  children: ReactNode;
}) {
  const { t } = useI18n();
  const [collapsed, setCollapsed] = useState(initialCollapsed);
  const [isMoreOpen, setMoreOpen] = useState(false);
  const tabItems = items.filter((item) => item.inTabBar);
  const moreItems = items.filter((item) => !item.inTabBar);

  const toggleCollapsed = () => {
    const next = !collapsed;
    setCollapsed(next);
    document.cookie = sidebarCookie(next ? "collapsed" : "expanded");
  };

  return (
    <div className="min-h-dvh" style={{ "--sidebar-width": collapsed ? "4.5rem" : "16rem" } as CSSProperties}>
      <ServiceWorker />
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:fixed focus:top-3 focus:left-3 focus:z-50 focus:rounded-lg focus:border focus:border-line focus:bg-surface focus:px-4 focus:py-2"
      >
        {t("nav.skipToContent")}
      </a>

      <aside
        data-collapsed={collapsed || undefined}
        className="fixed inset-y-0 start-0 z-20 hidden w-(--sidebar-width) border-e border-line bg-canvas transition-[width] duration-(--motion-base) ease-(--ease-emphasized) lg:block"
      >
        <Sidebar
          items={items}
          top={switcher?.(undefined, collapsed)}
          replacement={sidebarReplacement}
          me={me}
          collapsed={collapsed}
          onToggleCollapsed={toggleCollapsed}
        />
      </aside>

      <div className="transition-[padding] duration-(--motion-base) ease-(--ease-emphasized) lg:ps-(--sidebar-width)">
        {showPhoneTopBar ? (
        <PhoneTopBar
          title={title}
          context={context}
          action={
            showTabBar ? undefined : (
              <button
                type="button"
                onClick={() => setMoreOpen(true)}
                aria-label={t("account.menu")}
                aria-haspopup="dialog"
                aria-expanded={isMoreOpen}
                className="flex size-11 cursor-pointer items-center justify-center rounded-full"
              >
                <UserAvatar user={me.user} />
              </button>
            )
          }
        />
        ) : null}
        <main
          id="main"
          tabIndex={-1}
          className={cn(
            "mx-auto w-full px-4 py-6 focus:outline-none sm:px-6 lg:px-8 lg:py-8",
            isWide ? "max-w-[100rem]" : "max-w-6xl",
            showTabBar && "pb-[calc(6.5rem+env(safe-area-inset-bottom))] lg:pb-8",
          )}
        >
          {children}
        </main>
      </div>

      {showTabBar ? (
        <PhoneTabBar
          items={tabItems}
          isMoreActive={moreItems.some((item) => item.isActive)}
          isMoreOpen={isMoreOpen}
          onOpenMore={() => setMoreOpen(true)}
        />
      ) : null}
      <MoreSheet
        open={isMoreOpen}
        onClose={() => setMoreOpen(false)}
        items={showTabBar ? moreItems : []}
        top={switcher ? (onNavigate) => switcher(onNavigate) : undefined}
        me={me}
      />
    </div>
  );
}
