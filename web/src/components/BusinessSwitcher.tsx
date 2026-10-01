"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useId, useRef, useState } from "react";

import type { UserMembershipView } from "@/api/types";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";
import { countryFlag } from "@/lib/countries";
import { HOME_PATH, businessPath, sectionFromPathname } from "@/lib/navigation";

import { IconBuilding, IconCheck, IconChevronDown } from "./icons";

/**
 * The current business and a menu to jump to another one, keeping the
 * open section (bookings stay bookings).
 */
export function BusinessSwitcher({
  memberships,
  currentBusinessId,
  currentBusinessName,
  onNavigate,
}: {
  memberships: readonly UserMembershipView[];
  currentBusinessId: string;
  currentBusinessName: string;
  onNavigate?: () => void;
}) {
  const { t } = useI18n();
  const pathname = usePathname();
  const section = sectionFromPathname(pathname) ?? "dashboard";
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const menuId = useId();

  useEffect(() => {
    if (!open) {
      return;
    }
    const closeOnOutside = (event: PointerEvent) => {
      if (!containerRef.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setOpen(false);
      }
    };
    document.addEventListener("pointerdown", closeOnOutside);
    document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.removeEventListener("pointerdown", closeOnOutside);
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, [open]);

  const close = () => {
    setOpen(false);
    onNavigate?.();
  };

  return (
    <div ref={containerRef} className="relative">
      <button
        type="button"
        aria-expanded={open}
        aria-controls={menuId}
        onClick={() => setOpen((value) => !value)}
        className="flex w-full items-center gap-3 rounded-xl border border-line bg-surface px-3 py-2.5 text-left hover:border-line-strong"
      >
        <span className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-accent-soft text-accent" aria-hidden>
          <IconBuilding className="size-4" />
        </span>
        <span className="min-w-0 flex-1">
          <span className="block text-xs text-ink-subtle">{t("shell.switchBusiness")}</span>
          <span className="block truncate text-sm font-medium text-ink">{currentBusinessName}</span>
        </span>
        <IconChevronDown className={cn("size-4 shrink-0 text-ink-subtle transition-transform", open && "rotate-180")} aria-hidden />
      </button>

      {open ? (
        <div
          id={menuId}
          className="absolute inset-x-0 top-full z-30 mt-2 overflow-hidden rounded-xl border border-line bg-surface shadow-lg"
        >
          <ul className="max-h-72 overflow-y-auto py-1">
            {memberships.map((membership) => {
              const isCurrent = membership.business_id === currentBusinessId;
              return (
                <li key={membership.business_id}>
                  <Link
                    href={businessPath(membership.business_id, section)}
                    aria-current={isCurrent ? "page" : undefined}
                    onClick={close}
                    className="flex items-center gap-2 px-3 py-2 text-sm text-ink hover:bg-surface-muted"
                  >
                    <span aria-hidden>{countryFlag(membership.country_code)}</span>
                    <span className="min-w-0 flex-1 truncate">{membership.business_name}</span>
                    {isCurrent ? <IconCheck className="size-4 text-accent" aria-hidden /> : null}
                  </Link>
                </li>
              );
            })}
          </ul>
          <Link
            href={HOME_PATH}
            onClick={close}
            className="block border-t border-line px-3 py-2.5 text-sm font-medium text-accent hover:bg-surface-muted"
          >
            {t("nav.allBusinesses")}
          </Link>
        </div>
      ) : null}
    </div>
  );
}
