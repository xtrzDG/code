"use client";

import { useState } from "react";

import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";
import { LOGIN_PATH } from "@/lib/navigation";

import { IconLogout } from "../icons";

/** Ends the session (POST /api/auth/logout) and opens the sign-in page. */
export function SignOutButton({ className }: { className?: string }) {
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
      className={cn(
        "inline-flex items-center gap-2 rounded-lg px-2.5 py-2 text-sm text-ink-muted hover:bg-surface-muted hover:text-ink disabled:opacity-60",
        className,
      )}
    >
      <IconLogout className="size-4" aria-hidden />
      {isPending ? t("shell.signingOut") : t("shell.signOut")}
    </button>
  );
}
