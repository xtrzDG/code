"use client";

import Link from "next/link";
import type { ReactNode } from "react";

import { useI18n } from "@/i18n/client";
import { HOME_PATH } from "@/lib/navigation";

import { LanguageSwitcher } from "../LanguageSwitcher";
import { IconSparkles } from "../icons";
import { SignOutButton } from "./SignOutButton";

/**
 * Header of pages outside a business (business list, sign-in): brand,
 * language and, when signed in, sign-out.
 */
export function TopBar({ signedIn = false, actions }: { signedIn?: boolean; actions?: ReactNode }) {
  const { t } = useI18n();
  return (
    <header className="border-b border-line bg-surface">
      <div className="mx-auto flex h-16 w-full max-w-6xl items-center justify-between gap-3 px-4 sm:px-6">
        <Link href={signedIn ? HOME_PATH : "/"} className="flex min-w-0 items-center gap-2.5">
          <span className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-accent-solid text-on-accent" aria-hidden>
            <IconSparkles className="size-5" />
          </span>
          <span className="truncate text-sm font-semibold text-ink">{t("common.appName")}</span>
        </Link>
        <div className="flex items-center gap-1 sm:gap-3">
          {actions}
          <LanguageSwitcher compact />
          {signedIn ? <SignOutButton /> : null}
        </div>
      </div>
    </header>
  );
}
