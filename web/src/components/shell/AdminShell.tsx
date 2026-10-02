"use client";

import type { ReactNode } from "react";

import type { CurrentUserView } from "@/api/types";
import { useI18n } from "@/i18n/client";
import { ADMIN_PATH, HOME_PATH } from "@/lib/navigation";

import { IconBuilding, IconShield } from "../icons";
import { userDisplayName } from "./BusinessShell";
import { ShellFrame } from "./ShellFrame";

/** Frame of the platform admin pages (/admin/*). */
export function AdminShell({ me, children }: { me: CurrentUserView; children: ReactNode }) {
  const { t } = useI18n();
  return (
    <ShellFrame
      userName={userDisplayName(me.user)}
      context={t("shell.platformAdmin")}
      items={[
        { href: ADMIN_PATH, label: t("nav.admin"), icon: IconShield },
        { href: HOME_PATH, label: t("nav.allBusinesses"), icon: IconBuilding, secondary: true },
      ]}
    >
      {children}
    </ShellFrame>
  );
}
