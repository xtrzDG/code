"use client";

/**
 * The bottom tab bar on phones: Overview, Messages, Bookings, Assistant and
 * "More" (settings, the business switcher and the account). Every place is
 * at least 56 px tall, the bar sits above the home indicator (safe-area
 * inset) and a soft pill glides behind the current place.
 */

import { LayoutGroup } from "motion/react";
import * as m from "motion/react-m";
import Link from "next/link";
import { useId, type ComponentType } from "react";

import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";
import { springTransition } from "@/lib/motion";

import { IconMenu, type IconProps } from "../icons";
import { NavBadge } from "./NavBadge";
import type { ShellNavItem } from "./types";

const PLACE =
  "relative flex min-h-14 flex-1 flex-col items-center justify-center gap-1 rounded-xl px-1 text-[0.6875rem] leading-tight font-medium transition-colors";

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

  return (
    <LayoutGroup id={groupId}>
      <nav
        aria-label={t("navigation.tabBar")}
        className="fixed inset-x-0 bottom-0 z-30 border-t border-line bg-surface/85 pb-[env(safe-area-inset-bottom)] backdrop-blur-xl lg:hidden"
      >
        <ul className="mx-auto flex max-w-xl items-stretch gap-1 px-2 py-1">
          {items.map((item) => (
            <li key={item.key} className="flex flex-1">
              <Link
                href={item.href}
                aria-current={item.isActive ? "page" : undefined}
                className={cn(PLACE, item.isActive ? "text-accent-ink" : "text-ink-muted active:text-ink")}
              >
                {item.isActive ? <Marker /> : null}
                <span className="relative flex flex-col items-center gap-1">
                  <PlaceIcon icon={item.icon} isActive={item.isActive} badge={item.badge ?? 0} />
                  <span className="max-w-[4.5rem] truncate">{item.label}</span>
                </span>
              </Link>
            </li>
          ))}
          <li className="flex flex-1">
            <button
              type="button"
              onClick={onOpenMore}
              aria-haspopup="dialog"
              aria-expanded={isMoreOpen}
              className={cn(PLACE, "cursor-pointer", isMoreActive ? "text-accent-ink" : "text-ink-muted active:text-ink")}
            >
              {isMoreActive ? <Marker /> : null}
              <span className="relative flex flex-col items-center gap-1">
                <PlaceIcon icon={IconMenu} isActive={isMoreActive} badge={0} />
                <span>{t("navigation.more")}</span>
              </span>
            </button>
          </li>
        </ul>
      </nav>
    </LayoutGroup>
  );
}
