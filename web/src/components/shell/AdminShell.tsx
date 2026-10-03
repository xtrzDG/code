"use client";

import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

import type { CurrentUserView } from "@/api/types";
import { useI18n } from "@/i18n/client";
import { ADMIN_METRICS_PATH, ADMIN_PATH, ADMIN_SECURITY_PATH, HOME_PATH } from "@/lib/navigation";

import { IconBuilding, IconGauge, IconKey, IconShield } from "../icons";
import { ShellFrame } from "./ShellFrame";

/** Frame of the platform admin pages (/admin/*): the clients, the growth metrics, the encryption keys, and the way back to the businesses. */
export function AdminShell({ me, initialCollapsed = false, children }: { me: CurrentUserView; initialCollapsed?: boolean; children: ReactNode }) {
  const { t } = useI18n();
  const pathname = usePathname();
  const isSecurityPage = pathname === ADMIN_SECURITY_PATH || pathname.startsWith(`${ADMIN_SECURITY_PATH}/`);
  const isMetricsPage = pathname === ADMIN_METRICS_PATH || pathname.startsWith(`${ADMIN_METRICS_PATH}/`);
  const isAdminPage = !isSecurityPage && !isMetricsPage && (pathname === ADMIN_PATH || pathname.startsWith(`${ADMIN_PATH}/`));
  return (
    <ShellFrame
      me={me}
      initialCollapsed={initialCollapsed}
      context={t("shell.platformAdmin")}
      title={isSecurityPage ? t("adminSecurity.nav") : isMetricsPage ? t("adminMetrics.nav") : t("nav.admin")}
      items={[
        { key: "admin", href: ADMIN_PATH, label: t("nav.admin"), icon: IconShield, isActive: isAdminPage, inTabBar: true },
        {
          key: "metrics",
          href: ADMIN_METRICS_PATH,
          label: t("adminMetrics.nav"),
          icon: IconGauge,
          isActive: isMetricsPage,
          inTabBar: true,
        },
        {
          key: "security",
          href: ADMIN_SECURITY_PATH,
          label: t("adminSecurity.nav"),
          icon: IconKey,
          isActive: isSecurityPage,
          inTabBar: true,
        },
        { key: "businesses", href: HOME_PATH, label: t("nav.allBusinesses"), icon: IconBuilding, isActive: false, inTabBar: true },
      ]}
    >
      {children}
    </ShellFrame>
  );
}
