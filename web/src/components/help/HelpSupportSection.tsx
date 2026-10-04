"use client";

/**
 * "Help and support" in the account panel: the help center, "What's new"
 * (with how many entries are new), the platform's status page, and the
 * support team's WhatsApp, Telegram and e-mail.
 */

import Link from "next/link";
import { useId } from "react";

import { IconHelp, IconPulse, IconSparkles } from "@/components/icons";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";
import { unreadKeys } from "@/lib/help/changelog";
import { HELP_PATH, STATUS_PATH, WHATS_NEW_PATH } from "@/lib/help/helpTopics";

import { CHANGELOG } from "../../../content/changelog";

import { SupportContacts } from "./SupportContacts";
import { useHelpProgress } from "./useHelp";

/** How many "What's new" entries the signed-in person has not read (0 until known). */
export function useUnreadChangelog(): number {
  const { progress } = useHelpProgress();
  return progress.data ? unreadKeys(CHANGELOG, progress.data.changelog_read_key).length : 0;
}

/** A dot on the account button while "What's new" has something unread. */
export function ChangelogDot({ className }: { className?: string }) {
  const unread = useUnreadChangelog();
  return unread > 0 ? (
    <span data-changelog-dot="" aria-hidden className={cn("size-2.5 rounded-full bg-accent ring-2 ring-canvas", className)} />
  ) : null;
}

export function HelpSupportSection({ rowClassName, onNavigate }: { rowClassName: string; onNavigate?: () => void }) {
  const { t, tp } = useI18n();
  const titleId = useId();
  const unread = useUnreadChangelog();

  return (
    <section aria-labelledby={titleId} className="space-y-0.5 border-t border-line pt-2">
      <p id={titleId} className="px-2.5 pt-0.5 pb-1 text-xs font-medium text-ink-subtle">
        {t("helpCenter.support.title")}
      </p>
      <Link href={HELP_PATH} onClick={onNavigate} className={rowClassName}>
        <IconHelp className="size-4 shrink-0" aria-hidden />
        {t("helpCenter.support.center")}
      </Link>
      <Link href={WHATS_NEW_PATH} onClick={onNavigate} className={rowClassName}>
        <IconSparkles className="size-4 shrink-0" aria-hidden />
        <span className="min-w-0 flex-1">{t("helpCenter.support.whatsNew")}</span>
        {unread > 0 ? (
          <span className="inline-flex items-center gap-1.5 rounded-full bg-accent-soft px-2 py-0.5 text-xs font-medium text-accent-ink">
            <span className="size-1.5 rounded-full bg-accent" aria-hidden />
            {tp("helpCenter.support.unread", unread)}
          </span>
        ) : null}
      </Link>
      <Link href={STATUS_PATH} onClick={onNavigate} className={rowClassName}>
        <IconPulse className="size-4 shrink-0" aria-hidden />
        {t("helpCenter.support.status")}
      </Link>
      <SupportContacts rowClassName={rowClassName} />
    </section>
  );
}
