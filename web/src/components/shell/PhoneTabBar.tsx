"use client";

/**
 * The bottom tab bar on phones: Overview, Messages, Bookings, Assistant and
 * "More" (settings, the business switcher and the account). Every place is
 * at least 56 px tall, the bar sits above the home indicator (safe-area
 * inset) and a soft pill glides behind the current place. Above its end
 * floats the page's primary action, when the page has one (usePhoneFab).
 */

import { LayoutGroup } from "motion/react";
import * as m from "motion/react-m";
import Link from "next/link";
import { useId, type ComponentType } from "react";

import { Fab, usePhoneChromeSnapshot } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";
import { springTransition } from "@/lib/motion";

import { IconMenu, type IconProps } from "../icons";
import { NavBadge } from "./NavBadge";
import type { ShellNavItem } from "./types";

const PLACE =
  "relative flex min-h-14 min-w-0 flex-1 flex-col items-center justify-center gap-1 rounded-xl px-1 text-[0.6875rem] leading-tight font-medium transition-colors";

/**
 * A name of two words wraps between them onto a second line; a word never
 * breaks inside: the browser hyphenates it where it knows the language
 * (`lang` of the page), and a word still too wide ends with "…" rather
 * than spilling a letter onto the next line ("Posteingan-g"). Sections
 * with a long name have a shorter one for the tab bar (SECTION_TAB_LABELS).
 */
const LABEL = "line-clamp-2 max-w-full text-center break-normal text-ellipsis hyphens-auto";

function Marker() {
  return (
    <m.span
      layoutId="tab-bar-marker"
      transition={springTransition("snappy")}
      aria-hidden
      className="absolute inset-x-1.5 inset-y-1 rounded-xl bg-accent-soft"
    />
  );
}

function PlaceIcon({ icon: Icon, isActive, badge }: { icon: ComponentType<IconProps>; isActive: boolean; badge: number }) {
  return (
    <span className="relative">
      <Icon className={cn("size-[1.375rem] transition-transform", isActive ? "scale-105 text-accent" : "text-ink-subtle")} aria-hidden />
      {badge > 0 ? <NavBadge count={badge} size="sm" className="absolute -end-3 -top-1.5 ring-2 ring-surface" /> : null}
    </span>
  );
}

export function PhoneTabBar({
  items,
  isMoreActive,
  isMoreOpen,
  onOpenMore,
}: {
  items: readonly ShellNavItem[];
  /** The page is one of those under "More" (settings). */
  isMoreActive: boolean;
  isMoreOpen: boolean;
  onOpenMore: () => void;
}) {
  const { t } = useI18n();
  const groupId = useId();
  const { fab } = usePhoneChromeSnapshot();

  return (
    <LayoutGroup id={groupId}>
      {fab ? (
        <div className="pointer-events-none fixed end-4 bottom-[calc(4.75rem+env(safe-area-inset-bottom))] z-30 lg:hidden">
          <Fab key={fab.label} label={fab.label} icon={fab.icon} onClick={fab.run} opensDialog={fab.opensDialog} />
        </div>
      ) : null}
      <nav
        aria-label={t("navigation.tabBar")}
        className="fixed inset-x-0 bottom-0 z-30 border-t border-line bg-surface/85 pb-[env(safe-area-inset-bottom)] backdrop-blur-xl lg:hidden"
      >
        <ul className="mx-auto flex max-w-xl items-stretch gap-1 px-2 py-1">
          {items.map((item) => (
            <li key={item.key} className="flex min-w-0 flex-1">
              <Link
                href={item.href}
                aria-current={item.isActive ? "page" : undefined}
                className={cn(PLACE, item.isActive ? "text-accent-ink" : "text-ink-muted active:text-ink")}
              >
                {item.isActive ? <Marker /> : null}
                <span className="relative flex max-w-full flex-col items-center gap-1">
                  <PlaceIcon icon={item.icon} isActive={item.isActive} badge={item.badge ?? 0} />
                  <span data-tab-label className={LABEL}>
                    {item.tabLabel ?? item.label}
                  </span>
                </span>
              </Link>
            </li>
          ))}
          <li className="flex min-w-0 flex-1">
            <button
              type="button"
              onClick={onOpenMore}
              aria-haspopup="dialog"
              aria-expanded={isMoreOpen}
              className={cn(PLACE, "cursor-pointer", isMoreActive ? "text-accent-ink" : "text-ink-muted active:text-ink")}
            >
              {isMoreActive ? <Marker /> : null}
              <span className="relative flex max-w-full flex-col items-center gap-1">
                <PlaceIcon icon={IconMenu} isActive={isMoreActive} badge={0} />
                <span data-tab-label className={LABEL}>
                  {t("navigation.more")}
                </span>
              </span>
            </button>
          </li>
        </ul>
      </nav>
    </LayoutGroup>
  );
}
