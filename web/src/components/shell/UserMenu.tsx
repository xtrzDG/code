"use client";

/**
 * The signed-in person at the bottom of the sidebar; pressing it opens the
 * account panel (language, theme, install, businesses, sign out) above it.
 * The panel is a native popover: it sits in the top layer (nothing clips
 * it), and Escape or a press outside closes it.
 */

import { useId, useRef } from "react";

import type { CurrentUserView } from "@/api/types";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";

import { ChangelogDot } from "../help/HelpSupportSection";
import { IconChevronDown } from "../icons";
import { AccountPanel } from "./AccountPanel";
import { UserAvatar, userContact, userDisplayName } from "./UserAvatar";

const PANEL_WIDTH_PX = 288;
const GAP_PX = 8;
const MIN_PANEL_HEIGHT_PX = 240;

export function UserMenu({ me, collapsed = false }: { me: CurrentUserView; collapsed?: boolean }) {
  const { t } = useI18n();
  const panelId = useId();
  const buttonRef = useRef<HTMLButtonElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);
  const name = userDisplayName(me.user);
  const contact = userContact(me.user);

  // Opens upwards from the button, inside the window (no anchor positioning in every browser yet).
  const place = () => {
    const button = buttonRef.current;
    const panel = panelRef.current;
    if (!button || !panel) {
      return;
    }
    const rect = button.getBoundingClientRect();
    const isRtl = document.documentElement.dir === "rtl";
    const left = isRtl ? Math.max(GAP_PX, rect.right - PANEL_WIDTH_PX) : Math.min(rect.left, window.innerWidth - PANEL_WIDTH_PX - GAP_PX);
    panel.style.left = `${Math.max(GAP_PX, left)}px`;
    panel.style.bottom = `${window.innerHeight - rect.top + GAP_PX}px`;
    panel.style.maxHeight = `${Math.max(MIN_PANEL_HEIGHT_PX, rect.top - GAP_PX * 2)}px`;
  };

  const closeAfterNavigation = () => panelRef.current?.hidePopover();

  return (
    <>
      <button
        ref={buttonRef}
        type="button"
        popoverTarget={panelId}
        onClick={place}
        aria-label={collapsed ? t("account.menu") : undefined}
        title={collapsed ? name : undefined}
        className={cn(
          "group flex w-full cursor-pointer items-center gap-2.5 rounded-lg text-start transition-colors hover:bg-surface-muted",
          collapsed ? "justify-center p-1.5" : "px-2 py-1.5",
        )}
      >
        <span className="relative shrink-0">
          <UserAvatar user={me.user} />
          <ChangelogDot className="absolute -end-0.5 -top-0.5" />
        </span>
        {collapsed ? null : (
          <>
            <span className="min-w-0 flex-1">
              <span className="sr-only">{`${t("account.menu")}: `}</span>
              <span className="block truncate text-sm font-medium text-ink" data-user-content>
                <bdi>{name}</bdi>
              </span>
              {contact && contact !== name ? (
                <span className="block truncate text-xs text-ink-subtle" data-user-content>
                  <bdi dir="ltr">{contact}</bdi>
                </span>
              ) : null}
            </span>
            <IconChevronDown className="size-4 shrink-0 rotate-180 text-ink-subtle transition-transform group-hover:-translate-y-0.5" aria-hidden />
          </>
        )}
      </button>
      <div
        ref={panelRef}
        id={panelId}
        popover="auto"
        role="dialog"
        aria-label={t("account.menu")}
        className="user-menu-panel fixed inset-auto m-0 w-72 overflow-y-auto overscroll-contain rounded-2xl border border-line bg-surface p-2 text-ink shadow-2xl"
      >
        <AccountPanel me={me} onNavigate={closeAfterNavigation} />
      </div>
    </>
  );
}
