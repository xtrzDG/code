"use client";

/**
 * The sections in the sidebar: an icon and a name each, a marker that
 * glides to the open one, the open section's pages beneath it (the
 * Assistant's versions and autotests behind an "Advanced" disclosure) and
 * badges where something waits. Collapsed, only the icons stay, with their
 * names as tooltips and for screen readers.
 */

import { LayoutGroup } from "motion/react";
import * as m from "motion/react-m";
import Link from "next/link";
import { useId, useState } from "react";

import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";
import { springTransition, tweenTransition } from "@/lib/motion";

import { IconChevronRight } from "../icons";
import { NavBadge } from "./NavBadge";
import type { ShellNavItem, ShellSubLink } from "./types";

function SubPages({ pages, onNavigate }: { pages: readonly ShellSubLink[]; onNavigate?: () => void }) {
  const { t } = useI18n();
  const advanced = pages.filter((page) => page.isAdvanced);
  const regular = pages.filter((page) => !page.isAdvanced);
  const [showAdvanced, setShowAdvanced] = useState(() => advanced.some((page) => page.isActive));
  const advancedId = useId();
  const isAdvancedOpen = showAdvanced || advanced.some((page) => page.isActive);

  const renderPage = (page: ShellSubLink) => (
    <li key={page.href}>
      <Link
        href={page.href}
        onClick={onNavigate}
        onPointerEnter={page.isActive ? undefined : page.onPrefetch}
        onFocus={page.isActive ? undefined : page.onPrefetch}
        aria-current={page.isActive ? "page" : undefined}
        className={cn(
          "relative flex min-h-8 items-center gap-2 rounded-md py-1 ps-3 pe-2 text-[0.8125rem] leading-snug transition-colors pointer-coarse:min-h-11",
          page.isActive ? "font-medium text-ink" : "text-ink-muted hover:text-ink",
        )}
      >
        {page.isActive ? (
          <m.span
            layoutId="active-page"
            transition={springTransition("snappy")}
            aria-hidden
            className="absolute inset-y-1.5 -start-px w-0.5 rounded-full bg-accent-solid"
          />
        ) : null}
        {/* A long name (Georgian, Russian) wraps instead of being cut. */}
        <span className="min-w-0 [overflow-wrap:anywhere]">{page.label}</span>
        <NavBadge count={page.badge ?? 0} className="ms-auto" />
      </Link>
    </li>
  );

  return (
    <m.div
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: "auto" }}
      transition={tweenTransition("base", "emphasized")}
      className="overflow-hidden"
    >
      <ul className="ms-[1.3rem] mt-0.5 mb-1.5 space-y-0.5 border-s border-line">
        {regular.map(renderPage)}
        {advanced.length > 0 ? (
          <li>
            <button
              type="button"
              aria-expanded={isAdvancedOpen}
              aria-controls={advancedId}
              onClick={() => setShowAdvanced((value) => !value)}
              className="flex h-8 w-full cursor-pointer items-center gap-1.5 ps-3 pe-2 text-xs font-medium tracking-wide text-ink-subtle uppercase transition-colors hover:text-ink pointer-coarse:h-11"
            >
              <IconChevronRight
                className={cn("size-3.5 transition-transform rtl:-scale-x-100", isAdvancedOpen && "rotate-90 rtl:rotate-90")}
                aria-hidden
              />
              {t("navigation.advanced")}
            </button>
            {isAdvancedOpen ? (
              <ul id={advancedId} className="space-y-0.5">
                {advanced.map(renderPage)}
              </ul>
            ) : null}
          </li>
        ) : null}
      </ul>
    </m.div>
  );
}

export function SidebarNav({
  items,
  collapsed = false,
  onNavigate,
}: {
  items: readonly ShellNavItem[];
  collapsed?: boolean;
  onNavigate?: () => void;
}) {
  const { t, tp } = useI18n();
  const groupId = useId();
  const primary = items.filter((item) => !item.secondary);
  const secondary = items.filter((item) => item.secondary);

  const renderItem = (item: ShellNavItem) => {
    const Icon = item.icon;
    const badge = item.badge ?? 0;
    return (
      <li key={item.key}>
        <Link
          href={item.href}
          onClick={onNavigate}
          onPointerEnter={item.isActive ? undefined : item.onPrefetch}
          onFocus={item.isActive ? undefined : item.onPrefetch}
          aria-current={item.isActive ? "page" : undefined}
          title={collapsed ? item.label : undefined}
          className={cn(
            "group relative flex min-h-10 items-center gap-3 rounded-lg py-1.5 text-sm leading-snug transition-colors pointer-coarse:min-h-11",
            collapsed ? "justify-center px-0" : "px-2.5",
            item.isActive ? "font-medium text-ink" : "text-ink-muted hover:bg-surface-muted/60 hover:text-ink",
          )}
        >
          {item.isActive ? (
            // The marker glides from the old section to the new one (a shared layout animation).
            <m.span
              layoutId="active-section"
              transition={springTransition("layout")}
              className="absolute inset-0 rounded-lg bg-surface-muted ring-1 ring-line ring-inset"
              aria-hidden
            />
          ) : null}
          <span className="relative">
            <Icon
              className={cn(
                "size-[1.125rem] shrink-0 transition-transform duration-(--motion-fast) group-hover:scale-110",
                item.isActive ? "text-accent" : "text-ink-subtle",
              )}
              aria-hidden
            />
            {collapsed && badge > 0 ? (
              <span aria-hidden className="absolute -end-1.5 -top-1 size-2.5 rounded-full bg-danger-solid ring-2 ring-canvas" />
            ) : null}
          </span>
          <span className={cn("relative min-w-0 [overflow-wrap:anywhere]", collapsed && "sr-only")}>{item.label}</span>
          {collapsed ? (
            badge > 0 ? <span className="sr-only">{`, ${tp("navigation.waiting", badge)}`}</span> : null
          ) : (
            <NavBadge count={badge} className="relative ms-auto" />
          )}
        </Link>
        {item.isActive && !collapsed && item.pages && item.pages.length > 1 ? (
          <SubPages pages={item.pages} onNavigate={onNavigate} />
        ) : null}
      </li>
    );
  };

  return (
    // Its own group: the sidebar and the phone sheet each move their own marker.
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
