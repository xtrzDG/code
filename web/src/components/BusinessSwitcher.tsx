"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useId, useRef, useState } from "react";

import type { UserMembershipView } from "@/api/types";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";
import { countryFlag } from "@/lib/countries";
import { CREATE_PATH, HOME_PATH, samePageIn } from "@/lib/navigation";

import { IconBuilding, IconCheck, IconChevronDown, IconPlus } from "./icons";

/**
 * The current business and a menu to jump to another one, keeping the
 * open page (bookings stay bookings). `compact` (the collapsed sidebar)
 * shows only the business's initial; the menu then opens to the side.
 */
export function BusinessSwitcher({
  memberships,
  currentBusinessId,
  currentBusinessName,
  onNavigate,
  compact = false,
}: {
  memberships: readonly UserMembershipView[];
  currentBusinessId: string;
  currentBusinessName: string;
  onNavigate?: () => void;
  compact?: boolean;
}) {
  const { t } = useI18n();
  const pathname = usePathname();
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
        aria-label={compact ? `${t("shell.switchBusiness")}: ${currentBusinessName}` : undefined}
        title={compact ? currentBusinessName : undefined}
        className={cn(
          "flex w-full cursor-pointer items-center gap-2.5 rounded-lg border border-line bg-surface text-start transition-colors hover:bg-surface-muted",
          compact ? "justify-center p-1.5" : "px-2.5 py-2",
        )}
      >
        <span className="flex size-8 shrink-0 items-center justify-center rounded-md border border-line bg-surface-muted text-ink-muted" aria-hidden>
          {compact ? <span className="text-sm font-semibold text-ink">{Array.from(currentBusinessName)[0]?.toLocaleUpperCase()}</span> : <IconBuilding className="size-4" />}
        </span>
        {compact ? null : (
          <>
            <span className="min-w-0 flex-1">
              <span className="block text-xs text-ink-subtle">{t("shell.switchBusiness")}</span>
              <span className="block truncate text-sm font-medium text-ink">{currentBusinessName}</span>
            </span>
            <IconChevronDown className={cn("size-4 shrink-0 text-ink-subtle transition-transform", open && "rotate-180")} aria-hidden />
          </>
        )}
      </button>

      {open ? (
        <div
          id={menuId}
          className={cn(
            "absolute z-30 overflow-hidden rounded-xl border border-line bg-surface shadow-lg",
            compact ? "start-full top-0 ms-2 w-64" : "inset-x-0 top-full mt-1.5",
          )}
        >
          <ul className="max-h-72 overflow-y-auto py-1">
            {memberships.map((membership) => {
              const isCurrent = membership.business_id === currentBusinessId;
              return (
                <li key={membership.business_id}>
                  <Link
                    href={samePageIn(membership.business_id, pathname)}
                    aria-current={isCurrent ? "page" : undefined}
                    onClick={close}
                    className="flex min-h-10 items-center gap-2 px-3 py-2 text-sm text-ink hover:bg-surface-muted"
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
            href={CREATE_PATH}
            onClick={close}
            className="flex items-center gap-2 border-t border-line px-3 py-2.5 text-sm font-medium text-ink hover:bg-surface-muted"
          >
            <IconPlus className="size-4 text-accent" aria-hidden />
            {t("tunnel.newAssistant")}
          </Link>
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
