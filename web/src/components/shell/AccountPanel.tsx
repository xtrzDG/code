"use client";

/**
 * Who is signed in and their preferences: the interface language, the
 * theme, the chime when someone needs a person, installing the cabinet as
 * an app, all businesses, Account → Security (the authenticator app), the
 * platform admin (for admins) and signing out. Shown by the user menu at the bottom
 * of the sidebar, and inside "More" on phones.
 */

import Link from "next/link";
import { useId, useState } from "react";

import type { CurrentUserView } from "@/api/types";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";
import { ACCOUNT_SECURITY_PATH, ADMIN_PATH, HOME_PATH } from "@/lib/navigation";

import { LanguageSwitcher } from "../LanguageSwitcher";
import { IconBuilding, IconDownload, IconKey, IconShield } from "../icons";
import { ThemeSwitcher } from "../theme/ThemeSwitcher";
import { ChimeSetting } from "./ChimeSetting";
import { SignOutButton } from "./SignOutButton";
import { UserAvatar, userDisplayName, userContact } from "./UserAvatar";
import { useInstallPrompt } from "./useInstallPrompt";

const ROW = "flex min-h-10 w-full items-center gap-3 rounded-lg px-2.5 text-sm text-ink-muted transition-colors hover:bg-surface-muted hover:text-ink pointer-coarse:min-h-11";

function InstallRow() {
  const { t } = useI18n();
  const { mode, install } = useInstallPrompt();
  const [showSteps, setShowSteps] = useState(false);
  const stepsId = useId();

  if (mode === "installed" || mode === "unavailable") {
    return null;
  }
  return (
    <div>
      <button
        type="button"
        className={cn(ROW, "cursor-pointer text-start")}
        aria-expanded={mode === "ios" ? showSteps : undefined}
        aria-controls={mode === "ios" ? stepsId : undefined}
        onClick={() => (mode === "prompt" ? void install() : setShowSteps((value) => !value))}
      >
        <IconDownload className="size-4 shrink-0" aria-hidden />
        <span className="min-w-0">
          <span className="block font-medium text-ink">{t("account.install")}</span>
          <span className="block text-xs text-ink-subtle">{t("account.installHint")}</span>
        </span>
      </button>
      {mode === "ios" && showSteps ? (
        <div id={stepsId} className="mx-2.5 mt-1 mb-2 rounded-lg bg-surface-muted p-3 text-sm">
          <p className="font-medium text-ink">{t("account.installIosTitle")}</p>
          <p className="mt-1 text-ink-muted">{t("account.installIosSteps")}</p>
        </div>
      ) : null}
    </div>
  );
}

export function AccountPanel({ me, onNavigate }: { me: CurrentUserView; onNavigate?: () => void }) {
  const { t } = useI18n();
  const name = userDisplayName(me.user);
  const contact = userContact(me.user);

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3 px-2.5 pt-1">
        <UserAvatar user={me.user} className="size-10 text-sm" />
        <div className="min-w-0">
          <p className="text-xs text-ink-subtle">{t("account.signedInAs")}</p>
          <p className="truncate text-sm font-semibold text-ink" title={name}>
            {name}
          </p>
          {contact && contact !== name ? <p className="truncate text-xs text-ink-muted">{contact}</p> : null}
        </div>
      </div>

      <section aria-label={t("account.preferences")} className="space-y-2.5 border-t border-line px-2.5 pt-3">
        <LanguageSwitcher className="justify-between [&>div]:w-40" />
        <div className="flex items-center justify-between gap-3">
          <span className="text-sm text-ink-muted" aria-hidden>
            {t("theme.label")}
          </span>
          <ThemeSwitcher />
        </div>
      </section>

      <div className="border-t border-line pt-2.5">
        <ChimeSetting />
      </div>

      <div className="space-y-0.5 border-t border-line pt-2">
        <InstallRow />
        <Link href={HOME_PATH} onClick={onNavigate} className={ROW}>
          <IconBuilding className="size-4 shrink-0" aria-hidden />
          {t("account.businesses")}
        </Link>
        <Link href={ACCOUNT_SECURITY_PATH} onClick={onNavigate} className={ROW}>
          <IconKey className="size-4 shrink-0" aria-hidden />
          {t("security.menu")}
        </Link>
        {me.user.is_platform_admin ? (
          <Link href={ADMIN_PATH} onClick={onNavigate} className={ROW}>
            <IconShield className="size-4 shrink-0" aria-hidden />
            {t("account.admin")}
          </Link>
        ) : null}
        <SignOutButton className={cn(ROW, "h-auto")} />
      </div>
    </div>
  );
}
