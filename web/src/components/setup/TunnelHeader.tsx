"use client";

/**
 * The tunnel's top bar: the mark, the progress rail in the middle, whether
 * the answers are saved, the interface language and the way out ("Save
 * and exit"). Everything else of the cabinet stays out of sight.
 */

import Link from "next/link";
import type { ReactNode } from "react";

import { IconCheck, IconSparkles, IconX } from "@/components/icons";
import { LanguageSwitcher } from "@/components/LanguageSwitcher";
import { SignOutButton } from "@/components/shell/SignOutButton";
import { Spinner } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";

export type SaveState = "idle" | "saving" | "saved" | "failed";

function SaveStatus({ state }: { state: SaveState }) {
  const { t } = useI18n();
  if (state === "idle") {
    return null;
  }
  return (
    <span
      className={cn(
        "hidden items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium md:inline-flex",
        state === "failed" ? "bg-warning-soft text-warning" : "bg-surface-muted/70 text-ink-muted",
      )}
    >
      {state === "saving" ? <Spinner size="sm" /> : state === "saved" ? <IconCheck className="size-3.5 text-success" aria-hidden /> : null}
      {state === "saving" ? t("tunnel.saving") : state === "saved" ? t("tunnel.saved") : t("tunnel.saveFailed")}
    </span>
  );
}

export function TunnelHeader({
  rail,
  saveState,
  exitHref,
  homeHref,
}: {
  rail: ReactNode;
  saveState: SaveState;
  /** Where "Save and exit" leads; none offers signing out instead (an account with nothing else to open). */
  exitHref: string | null;
  homeHref: string;
}) {
  const { t } = useI18n();
  return (
    <header className="relative z-20 mx-auto flex w-full max-w-6xl items-center gap-3 px-4 pt-[max(0.75rem,env(safe-area-inset-top))] pb-2 sm:gap-6 sm:px-6 sm:pt-5">
      <Link
        href={homeHref}
        title={t("common.appName")}
        className="flex size-9 shrink-0 items-center justify-center rounded-xl bg-accent-solid text-on-accent shadow-[0_8px_24px_-8px_var(--accent-solid)]"
      >
        <IconSparkles className="size-5" aria-hidden />
        <span className="sr-only">{t("common.appName")}</span>
      </Link>
      {rail}
      <div className="flex shrink-0 items-center gap-2">
        <span aria-live="polite" className="contents">
          <SaveStatus state={saveState} />
        </span>
        <LanguageSwitcher compact className="max-sm:hidden" />
        {exitHref ? (
          <Link
            href={exitHref}
            className="inline-flex min-h-9 items-center gap-1.5 rounded-lg border border-line bg-surface/70 px-2.5 text-sm font-medium text-ink backdrop-blur hover:bg-surface-muted"
          >
            <IconX className="size-4" aria-hidden />
            <span className="max-sm:sr-only">{t("tunnel.exit")}</span>
          </Link>
        ) : (
          <SignOutButton iconOnlyOnPhones />
        )}
      </div>
    </header>
  );
}
