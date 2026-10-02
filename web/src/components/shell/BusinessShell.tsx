"use client";

import type { ComponentType, ReactNode } from "react";

import { useI18n } from "@/i18n/client";
import { ADMIN_PATH, BUSINESS_SECTIONS, BUSINESS_SECTION_LABELS, businessPath, type BusinessSection } from "@/lib/navigation";

import { BusinessSwitcher } from "../BusinessSwitcher";
import { useBusiness } from "../business/BusinessContext";
import {
  IconBook,
  IconCalendar,
  IconCard,
  IconChat,
  IconClipboard,
  IconGauge,
  IconHandoff,
  IconInbox,
  IconPlug,
  IconSettings,
  IconShield,
  IconSparkles,
  type IconProps,
} from "../icons";
import { ShellFrame, type ShellNavItem } from "./ShellFrame";

const SECTION_ICONS: Record<BusinessSection, ComponentType<IconProps>> = {
  onboarding: IconClipboard,
  dashboard: IconGauge,
  conversations: IconChat,
  bookings: IconCalendar,
  leads: IconInbox,
  handoffs: IconHandoff,
  knowledge: IconBook,
  assistant: IconSparkles,
  channels: IconPlug,
  billing: IconCard,
  settings: IconSettings,
};

/** Name to show for the signed-in user: display name, else phone or e-mail. */
export function userDisplayName(user: { display_name?: string | null; phone_number?: string | null; email?: string | null }): string {
  return user.display_name || user.phone_number || user.email || "";
}

/**
 * Sidebar of /b/[businessId]/*: the sections of concept section 8.
 * `prefetch` loads a section's first data while its link is under the
 * pointer or focused, so the section opens with it.
 */
export function BusinessShell({
  children,
  prefetch = {},
}: {
  children: ReactNode;
  prefetch?: Partial<Record<BusinessSection, () => void>>;
}) {
  const { t } = useI18n();
  const { business, me, isPlatformAdmin } = useBusiness();

  const items: ShellNavItem[] = BUSINESS_SECTIONS.map((section) => ({
    href: businessPath(business.id, section),
    label: t(BUSINESS_SECTION_LABELS[section]),
    icon: SECTION_ICONS[section],
    onPrefetch: prefetch[section],
  }));
  if (isPlatformAdmin) {
    items.push({ href: ADMIN_PATH, label: t("nav.admin"), icon: IconShield, secondary: true });
  }

  return (
    <ShellFrame
      items={items}
      context={business.name}
      userName={userDisplayName(me.user)}
      sidebarTop={(onNavigate) => (
        <BusinessSwitcher
          memberships={me.memberships ?? []}
          currentBusinessId={business.id}
          currentBusinessName={business.name}
          onNavigate={onNavigate}
        />
      )}
    >
      {children}
    </ShellFrame>
  );
}
