"use client";

import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

import type { CurrentUserView } from "@/api/types";
import { useI18n } from "@/i18n/client";
import { ADMIN_METRICS_PATH, ADMIN_PATH, ADMIN_SECURITY_PATH, ADMIN_SYSTEM_PATH, HOME_PATH } from "@/lib/navigation";

import { IconBuilding, IconGauge, IconKey, IconPulse, IconShield } from "../icons";
import { ShellFrame } from "./ShellFrame";

/**
 * Frame of the platform admin pages (/admin/*): the clients, the platform's
 * health (System), the growth metrics, the encryption keys, and the way
 * back to the businesses.
 */
export function AdminShell({ me, initialCollapsed = false, children }: { me: CurrentUserView; initialCollapsed?: boolean; children: ReactNode }) {
  const { t } = useI18n();
  const pathname = usePathname();
  const isSecurityPage = pathname === ADMIN_SECURITY_PATH || pathname.startsWith(`${ADMIN_SECURITY_PATH}/`);
  const isMetricsPage = pathname === ADMIN_METRICS_PATH || pathname.startsWith(`${ADMIN_METRICS_PATH}/`);
  const isSystemPage = pathname === ADMIN_SYSTEM_PATH || pathname.startsWith(`${ADMIN_SYSTEM_PATH}/`);
  const isAdminPage =
    !isSecurityPage && !isMetricsPage && !isSystemPage && (pathname === ADMIN_PATH || pathname.startsWith(`${ADMIN_PATH}/`));
  const title = isSecurityPage
    ? t("adminSecurity.nav")
    : isMetricsPage
      ? t("adminMetrics.nav")
      : isSystemPage
        ? t("adminSystem.nav")
        : t("nav.admin");
  return (
    <ShellFrame
      me={me}
      initialCollapsed={initialCollapsed}
      context={t("shell.platformAdmin")}
      title={title}
      items={[
        { key: "admin", href: ADMIN_PATH, label: t("nav.admin"), icon: IconShield, isActive: isAdminPage, inTabBar: true },
        // On call from a phone: the platform's health is one tap away.
        { key: "system", href: ADMIN_SYSTEM_PATH, label: t("adminSystem.nav"), icon: IconPulse, isActive: isSystemPage, inTabBar: true },
        {
          key: "metrics",
          href: ADMIN_METRICS_PATH,
          label: t("adminMetrics.nav"),
          icon: IconGauge,
          isActive: isMetricsPage,
          // Phones: under "More", so the tab bar keeps room for its labels.
          inTabBar: false,
        },
        {
          key: "security",
          href: ADMIN_SECURITY_PATH,
          label: t("adminSecurity.nav"),
          icon: IconKey,
          isActive: isSecurityPage,
          // Phones: under "More" next to the metrics; System takes its tab.
          inTabBar: false,
        },
        { key: "businesses", href: HOME_PATH, label: t("nav.allBusinesses"), icon: IconBuilding, isActive: false, inTabBar: true },
      ]}
    >
      {children}
    </ShellFrame>
  );
}
