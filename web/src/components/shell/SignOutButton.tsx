"use client";

import { useState } from "react";

import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";
import { LOGIN_PATH } from "@/lib/navigation";

import { IconLogout } from "../icons";

const DEFAULT_LOOK =
  "inline-flex h-8 items-center gap-2 rounded-lg px-2.5 text-sm text-ink-muted transition-colors hover:bg-surface-muted hover:text-ink";

/**
 * Ends the session (POST /api/auth/logout) and opens the sign-in page.
 * `className` replaces the default look (a quiet button) when given.
 */
export function SignOutButton({ className, iconOnlyOnPhones = false }: { className?: string; iconOnlyOnPhones?: boolean }) {
  const { t } = useI18n();
  const [isPending, setPending] = useState(false);

  return (
    <button
      type="button"
      disabled={isPending}
      onClick={async () => {
        setPending(true);
        try {
          await fetch("/api/auth/logout", { method: "POST" });
        } finally {
          // A full load drops every bit of client state of the old session.
          window.location.assign(LOGIN_PATH);
        }
      }}
      className={cn("cursor-pointer disabled:opacity-60", className ?? DEFAULT_LOOK)}
    >
      <IconLogout className="size-4 shrink-0" aria-hidden />
      <span className={cn(iconOnlyOnPhones && "sr-only sm:not-sr-only")}>
        {isPending ? t("shell.signingOut") : t("shell.signOut")}
      </span>
    </button>
  );
}
