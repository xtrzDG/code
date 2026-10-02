"use client";

/**
 * Page frame of the signed-in cabinet: a sidebar on large screens and a
 * slide-in menu on phones (Sidebar), the top bar with the language and
 * theme switches (ShellTopBar) and the page. The navigation is passed in by
 * BusinessShell (business pages) or AdminShell (platform admin).
 */

import { useState, type ReactNode } from "react";

import { useI18n } from "@/i18n/client";

import { IconX } from "../icons";
import { useClosingContent } from "../ui/useClosingContent";
import { useModalDialog } from "../ui/useModalDialog";
import { ShellTopBar } from "./ShellTopBar";
import { SidebarContent, type ShellNavItem } from "./Sidebar";

export type { ShellNavItem } from "./Sidebar";

export function ShellFrame({
  items,
  sidebarTop,
  context,
  userName,
  children,
}: {
  items: readonly ShellNavItem[];
  /** Rendered above the navigation (the business switcher). */
  sidebarTop?: (onNavigate: () => void) => ReactNode;
  /** Shown before the section name in the top bar (the business name). */
  context?: string;
  userName: string;
  children: ReactNode;
}) {
  const { t } = useI18n();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const closeDrawer = () => setDrawerOpen(false);
  const drawer = useModalDialog(drawerOpen, closeDrawer);
  // The menu slides out with its links still in it.
  const menu = useClosingContent(drawerOpen, [] as const);

  return (
    <div className="min-h-dvh">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:fixed focus:top-3 focus:left-3 focus:z-50 focus:rounded-lg focus:border focus:border-line focus:bg-surface focus:px-4 focus:py-2"
      >
        {t("nav.skipToContent")}
      </a>

      <aside className="fixed inset-y-0 left-0 hidden w-64 border-r border-line bg-canvas lg:block">
        <SidebarContent items={items} top={sidebarTop?.(() => undefined)} userName={userName} />
      </aside>

      <dialog
        {...drawer}
        aria-label={t("nav.mainNavigation")}
        data-motion="drawer-start"
        className="m-0 h-dvh max-h-dvh w-[min(18rem,85vw)] max-w-none border-r border-line bg-canvas p-0 text-ink lg:hidden"
      >
        {menu.isMounted ? (
          <div className="relative h-full">
            <button
              type="button"
              onClick={closeDrawer}
              className="absolute top-4 right-3 z-10 rounded-lg p-1.5 text-ink-muted transition-colors hover:bg-surface-muted hover:text-ink"
              aria-label={t("nav.closeMenu")}
            >
              <IconX className="size-5" aria-hidden />
            </button>
            <SidebarContent items={items} top={sidebarTop?.(closeDrawer)} userName={userName} onNavigate={closeDrawer} />
          </div>
        ) : null}
      </dialog>

      <div className="lg:pl-64">
        <ShellTopBar context={context} items={items} isMenuOpen={drawerOpen} onOpenMenu={() => setDrawerOpen(true)} />
        <main
          id="main"
          tabIndex={-1}
          className="mx-auto w-full max-w-6xl px-4 py-6 focus:outline-none sm:px-6 lg:px-8 lg:py-8"
        >
          {children}
        </main>
      </div>
    </div>
  );
}
