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

const SAVE_STATES = ["saving", "saved", "failed"] as const;

/**
 * Whether the answers are saved, in a slot as wide as its longest text in
 * this language (all three are laid over each other; only the current one
 * shows), so the rail never moves when "Saved" comes or goes.
 */
function SaveStatus({ state }: { state: SaveState }) {
  const { t } = useI18n();
  const texts = { saving: t("tunnel.saving"), saved: t("tunnel.saved"), failed: t("tunnel.saveFailed") };
  return (
    <span className="hidden md:grid" data-save-slot>
      {SAVE_STATES.map((shown) => (
        <span
          key={shown}
          className={cn(
            "col-start-1 row-start-1 inline-flex items-center gap-1.5 justify-self-end rounded-full px-2.5 py-1 text-xs font-medium whitespace-nowrap",
            shown === "failed" ? "bg-warning-soft text-warning" : "bg-surface-muted/70 text-ink-muted",
            shown !== state && "invisible",
          )}
        >
          {shown === "saving" ? state === "saving" ? <Spinner size="sm" /> : <span className="size-4" /> : shown === "saved" ? <IconCheck className="size-3.5 text-success" aria-hidden /> : null}
          {texts[shown]}
        </span>
      ))}
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
  /**
   * Where "Save and exit" leads; null offers signing out instead (an
   * account with nothing else to open); false shows neither (the finale
   * has its own way into the cabinet).
   */
  exitHref: string | null | false;
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
        ) : exitHref === null ? (
          <SignOutButton iconOnlyOnPhones />
        ) : null}
      </div>
    </header>
  );
}
