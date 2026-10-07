"use client";

import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

import type { CurrentUserView } from "@/api/types";
import { useI18n } from "@/i18n/client";
import { canOpenAdminPage, type AdminPageKey } from "@/lib/adminPermissions";
import {
  ADMIN_METRICS_PATH,
  ADMIN_PARTNERS_PATH,
  ADMIN_PATH,
  ADMIN_SECURITY_PATH,
  ADMIN_SYSTEM_PATH,
  ADMIN_TEAM_PATH,
  HOME_PATH,
} from "@/lib/navigation";

import { IconBuilding, IconGauge, IconKey, IconLink, IconPulse, IconShield, IconUsers } from "../icons";
import { ShellFrame } from "./ShellFrame";
import type { ShellNavItem } from "./types";

function isUnder(pathname: string, path: string): boolean {
  return pathname === path || pathname.startsWith(`${path}/`);
}

/**
 * Frame of the platform admin pages (/admin/*): the clients, the platform's
 * health (System), the growth metrics, the encryption keys, the admin team,
 * and the way back to the businesses. Each admin sees the pages their role
 * opens (lib/adminPermissions.ts).
 */
export function AdminShell({ me, initialCollapsed = false, children }: { me: CurrentUserView; initialCollapsed?: boolean; children: ReactNode }) {
  const { t } = useI18n();
  const pathname = usePathname();
  const isSecurityPage = isUnder(pathname, ADMIN_SECURITY_PATH);
  const isMetricsPage = isUnder(pathname, ADMIN_METRICS_PATH);
  const isSystemPage = isUnder(pathname, ADMIN_SYSTEM_PATH);
  const isTeamPage = isUnder(pathname, ADMIN_TEAM_PATH);
  const isPartnersPage = isUnder(pathname, ADMIN_PARTNERS_PATH);
  const isAdminPage =
    !isSecurityPage && !isMetricsPage && !isSystemPage && !isTeamPage && !isPartnersPage && isUnder(pathname, ADMIN_PATH);
  const title = isSecurityPage
    ? t("adminSecurity.nav")
    : isMetricsPage
      ? t("adminMetrics.nav")
      : isSystemPage
        ? t("adminSystem.nav")
        : isTeamPage
          ? t("adminTeam.nav")
          : isPartnersPage
            ? t("adminPartners.nav")
            : t("nav.admin");
  const pages: (ShellNavItem & { key: AdminPageKey })[] = [
    { key: "admin", href: ADMIN_PATH, label: t("nav.admin"), icon: IconShield, isActive: isAdminPage, inTabBar: true },
    // On call from a phone: the platform's health is one tap away.
    { key: "system", href: ADMIN_SYSTEM_PATH, label: t("adminSystem.nav"), icon: IconPulse, isActive: isSystemPage, inTabBar: true },
    // Phones: the rest under "More", so the tab bar keeps room for its labels.
    { key: "metrics", href: ADMIN_METRICS_PATH, label: t("adminMetrics.nav"), icon: IconGauge, isActive: isMetricsPage, inTabBar: false },
    { key: "security", href: ADMIN_SECURITY_PATH, label: t("adminSecurity.nav"), icon: IconKey, isActive: isSecurityPage, inTabBar: false },
    { key: "team", href: ADMIN_TEAM_PATH, label: t("adminTeam.nav"), icon: IconUsers, isActive: isTeamPage, inTabBar: false },
    { key: "partners", href: ADMIN_PARTNERS_PATH, label: t("adminPartners.nav"), icon: IconLink, isActive: isPartnersPage, inTabBar: false },
  ];
  return (
    <ShellFrame
      me={me}
      initialCollapsed={initialCollapsed}
      context={t("shell.platformAdmin")}
      title={title}
      items={[
        ...pages.filter((page) => canOpenAdminPage(me, page.key)),
        { key: "businesses", href: HOME_PATH, label: t("nav.allBusinesses"), icon: IconBuilding, isActive: false, inTabBar: true },
      ]}
    >
      {children}
    </ShellFrame>
  );
}
