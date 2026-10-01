"use client";

/**
 * Page frame of the signed-in cabinet: a sidebar on large screens and a top
 * bar with a slide-in drawer on phones. The navigation is passed in by
 * BusinessShell (business pages) or AdminShell (platform admin).
 */

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState, type ComponentType, type ReactNode } from "react";

import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";
import { HOME_PATH } from "@/lib/navigation";

import { LanguageSwitcher } from "../LanguageSwitcher";
import { IconMenu, IconSparkles, IconX, type IconProps } from "../icons";
import { SignOutButton } from "./SignOutButton";

export interface ShellNavItem {
  href: string;
  label: string;
  icon: ComponentType<IconProps>;
  /** Shown after the main list, separated (e.g. platform admin). */
  secondary?: boolean;
}

function isActive(pathname: string, href: string): boolean {
  return pathname === href || pathname.startsWith(`${href}/`);
}

function Brand() {
  const { t } = useI18n();
  return (
    <Link href={HOME_PATH} className="flex items-center gap-2.5 rounded-lg">
      <span className="flex size-8 items-center justify-center rounded-lg bg-accent-solid text-on-accent" aria-hidden>
        <IconSparkles className="size-5" />
      </span>
      <span className="text-sm leading-tight font-semibold text-ink">{t("common.appName")}</span>
    </Link>
  );
}

function NavList({ items, onNavigate }: { items: readonly ShellNavItem[]; onNavigate?: () => void }) {
  const pathname = usePathname();
  const { t } = useI18n();
  const primary = items.filter((item) => !item.secondary);
  const secondary = items.filter((item) => item.secondary);

  const renderItem = (item: ShellNavItem) => {
    const active = isActive(pathname, item.href);
    const Icon = item.icon;
    return (
      <li key={item.href}>
        <Link
          href={item.href}
          onClick={onNavigate}
          aria-current={active ? "page" : undefined}
          className={cn(
            "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
            active ? "bg-accent-soft text-accent-ink" : "text-ink-muted hover:bg-surface-muted hover:text-ink",
          )}
        >
          <Icon className="size-5 shrink-0" aria-hidden />
          <span className="truncate">{item.label}</span>
        </Link>
      </li>
    );
  };

  return (
    <nav aria-label={t("nav.mainNavigation")}>
      <ul className="space-y-0.5">{primary.map(renderItem)}</ul>
      {secondary.length > 0 ? <ul className="mt-4 space-y-0.5 border-t border-line pt-4">{secondary.map(renderItem)}</ul> : null}
    </nav>
  );
}

function SidebarContent({
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
    <div className="flex h-full flex-col gap-5 overflow-y-auto px-4 py-5">
      <Brand />
      {top}
      <div className="flex-1">
        <NavList items={items} onNavigate={onNavigate} />
      </div>
      <div className="space-y-3 border-t border-line pt-4">
        <LanguageSwitcher compact />
        <p className="truncate px-1 text-xs text-ink-subtle" title={userName}>
          {t("shell.signedInAs", { name: userName })}
        </p>
        <SignOutButton className="w-full" />
      </div>
    </div>
  );
}

export function ShellFrame({
  items,
  sidebarTop,
  userName,
  children,
}: {
  items: readonly ShellNavItem[];
  /** Rendered above the navigation (the business switcher). */
  sidebarTop?: (onNavigate: () => void) => ReactNode;
  userName: string;
  children: ReactNode;
}) {
  const { t } = useI18n();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const drawerRef = useRef<HTMLDialogElement>(null);
  const closeDrawer = () => setDrawerOpen(false);

  useEffect(() => {
    const drawer = drawerRef.current;
    if (!drawer) {
      return;
    }
    if (drawerOpen && !drawer.open) {
      drawer.showModal();
    } else if (!drawerOpen && drawer.open) {
      drawer.close();
    }
  }, [drawerOpen]);

  return (
    <div className="min-h-dvh">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:fixed focus:top-3 focus:left-3 focus:z-50 focus:rounded-lg focus:bg-surface focus:px-4 focus:py-2 focus:shadow-lg"
      >
        {t("nav.skipToContent")}
      </a>

      <aside className="fixed inset-y-0 left-0 hidden w-72 border-r border-line bg-surface lg:block">
        <SidebarContent items={items} top={sidebarTop?.(() => undefined)} userName={userName} />
      </aside>

      <div className="sticky top-0 z-20 flex h-14 items-center justify-between gap-3 border-b border-line bg-surface/90 px-4 backdrop-blur lg:hidden">
        <Brand />
        <button
          type="button"
          onClick={() => setDrawerOpen(true)}
          aria-expanded={drawerOpen}
          className="-mr-2 rounded-lg p-2 text-ink-muted hover:bg-surface-muted hover:text-ink"
          aria-label={t("nav.openMenu")}
        >
          <IconMenu className="size-6" aria-hidden />
        </button>
      </div>

      <dialog
        ref={drawerRef}
        onClose={closeDrawer}
        onCancel={(event) => {
          event.preventDefault();
          closeDrawer();
        }}
        onMouseDown={(event) => {
          if (event.target === event.currentTarget) {
            closeDrawer();
          }
        }}
        aria-label={t("nav.mainNavigation")}
        className="m-0 h-dvh max-h-dvh w-[min(20rem,85vw)] max-w-none border-r border-line bg-surface p-0 text-ink lg:hidden"
      >
        {drawerOpen ? (
          <div className="relative h-full">
            <button
              type="button"
              onClick={closeDrawer}
              className="absolute top-4 right-3 z-10 rounded-lg p-1.5 text-ink-muted hover:bg-surface-muted hover:text-ink"
              aria-label={t("nav.closeMenu")}
            >
              <IconX className="size-5" aria-hidden />
            </button>
            <SidebarContent
              items={items}
              top={sidebarTop?.(closeDrawer)}
              userName={userName}
              onNavigate={closeDrawer}
            />
          </div>
        ) : null}
      </dialog>

      <div className="lg:pl-72">
        <main id="main" tabIndex={-1} className="mx-auto w-full max-w-6xl px-4 py-6 focus:outline-none sm:px-6 lg:px-10 lg:py-10">
          {children}
        </main>
      </div>
    </div>
  );
}
