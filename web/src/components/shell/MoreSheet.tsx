"use client";

/**
 * "More" on phones: a sheet that rises from the bottom with what does not
 * fit the tab bar (settings and their pages, the platform admin), the
 * business switcher and the account panel (language, theme, install, sign
 * out). A native modal dialog: focus stays inside, Escape and a press on
 * the backdrop close it.
 */

import Link from "next/link";
import type { ReactNode } from "react";

import type { CurrentUserView } from "@/api/types";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";

import { IconChevronRight, IconX } from "../icons";
import { useClosingContent } from "../ui/useClosingContent";
import { useModalDialog } from "../ui/useModalDialog";
import { AccountPanel } from "./AccountPanel";
import { NavBadge } from "./NavBadge";
import type { ShellNavItem } from "./types";

function MoreLinks({ items, onNavigate }: { items: readonly ShellNavItem[]; onNavigate: () => void }) {
  const { t } = useI18n();
  return (
    <nav aria-label={t("nav.mainNavigation")} className="space-y-4">
      {items.map((item) => {
        const Icon = item.icon;
        const pages = item.pages && item.pages.length > 1 ? item.pages : [item];
        return (
          <section key={item.key} aria-label={item.label}>
            <h3 className="mb-1.5 flex items-center gap-2 px-1 text-xs font-semibold tracking-wide text-ink-subtle uppercase">
              <Icon className="size-4" aria-hidden />
              {item.label}
            </h3>
            <ul className="overflow-hidden rounded-2xl border border-line bg-surface">
              {pages.map((page, index) => (
                <li key={page.href} className={cn(index > 0 && "border-t border-line")}>
                  <Link
                    href={page.href}
                    onClick={onNavigate}
                    aria-current={page.isActive ? "page" : undefined}
                    className={cn(
                      "flex min-h-12 items-center gap-3 px-4 text-sm transition-colors active:bg-surface-muted",
                      page.isActive ? "font-medium text-accent" : "text-ink",
                    )}
                  >
                    <span className="min-w-0 flex-1 py-2 [overflow-wrap:anywhere]">{page.label}</span>
                    <NavBadge count={page.badge ?? 0} />
                    <IconChevronRight className="size-4 shrink-0 text-ink-subtle rtl:-scale-x-100" aria-hidden />
                  </Link>
                </li>
              ))}
            </ul>
          </section>
        );
      })}
    </nav>
  );
}

export function MoreSheet({
  open,
  onClose,
  items,
  top,
  me,
}: {
  open: boolean;
  onClose: () => void;
  /** The places that are not in the tab bar. */
  items: readonly ShellNavItem[];
  /** Above them (the business switcher). */
  top?: (onNavigate: () => void) => ReactNode;
  me: CurrentUserView;
}) {
  const { t } = useI18n();
  const dialog = useModalDialog(open, onClose);
  // The sheet slides down with its content still in it.
  const content = useClosingContent(open, [] as const);

  return (
    <dialog
      {...dialog}
      aria-label={t("navigation.more")}
      data-motion="sheet-bottom"
      className="fixed inset-x-0 top-auto bottom-0 m-0 max-h-[88dvh] w-full max-w-none overflow-hidden rounded-t-3xl border-t border-line bg-canvas p-0 text-ink shadow-2xl lg:hidden"
    >
      {content.isMounted ? (
        <div className="flex max-h-[88dvh] flex-col">
          <div aria-hidden className="mx-auto mt-2.5 h-1.5 w-10 shrink-0 rounded-full bg-line-strong/60" />
          <header className="flex shrink-0 items-center justify-between px-5 pt-2 pb-3">
            <h2 className="text-lg font-semibold tracking-tight">{t("navigation.more")}</h2>
            <button
              type="button"
              onClick={onClose}
              aria-label={t("common.close")}
              className="flex size-11 cursor-pointer items-center justify-center rounded-full text-ink-muted transition-colors hover:bg-surface-muted hover:text-ink"
            >
              <IconX className="size-5" aria-hidden />
            </button>
          </header>
          <div className="min-h-0 flex-1 space-y-5 overflow-y-auto px-4 pb-[calc(1.25rem+env(safe-area-inset-bottom))]">
            {top?.(onClose)}
            {items.length > 0 ? <MoreLinks items={items} onNavigate={onClose} /> : null}
            <div className="rounded-2xl border border-line bg-surface p-2">
              <AccountPanel me={me} onNavigate={onClose} />
            </div>
          </div>
        </div>
      ) : null}
    </dialog>
  );
}
