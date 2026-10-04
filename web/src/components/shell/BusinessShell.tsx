"use client";

/**
 * The frame of /b/[businessId]/*. Once the assistant exists: five sections
 * (Overview, Inbox, Bookings, Assistant, Settings), the ones the
 * viewer's role opens, with badges where something waits; the open
 * section's pages under it in the sidebar; on phones Overview, Inbox,
 * Bookings and Assistant in the tab bar and the rest under "More". The
 * inbox (a list beside a conversation) uses the full width; an open
 * conversation takes the whole phone screen, its own bar on top. Before
 * that: one big "Create an AI assistant" entry, and every page shows the
 * invitation to create it. The setup flow itself (/b/{id}/setup) is full
 * screen, without the frame. Over the pages, owners see the changes their
 * customers do not get yet, with "Apply changes" (components/assistant),
 * and the setup guide's progress ring until the guide is finished; the
 * first customers and bookings are celebrated with a toast (components/
 * setupGuide). While platform support looks into the cabinet, a banner
 * over the pages says who, why and until when (components/shell/
 * SupportBanner).
 */

import { usePathname } from "next/navigation";
import type { ComponentType, ReactNode } from "react";

import { useI18n } from "@/i18n/client";
import { sectionBadge, pageBadge } from "@/lib/inboxBadges";
import { ADMIN_PATH, businessLocation, businessPath, isConversationPath, type BusinessPage } from "@/lib/navigation";
import { SECTION_LABELS, canOpenPage, pageLabel, sectionOf, visiblePages, visibleSections, type BusinessSection } from "@/lib/sections";

import { ApplyChangesProvider } from "../assistant/ApplyChangesContext";
import { MilestoneCelebrations } from "../setupGuide/MilestoneCelebrations";
import { SetupRing } from "../setupGuide/SetupRing";
import { PendingChangesBanner } from "../assistant/PendingChangesBanner";
import { BusinessSwitcher } from "../BusinessSwitcher";
import { useBusiness } from "../business/BusinessContext";
import { IconCalendar, IconGauge, IconInbox, IconSettings, IconShield, IconSparkles, type IconProps } from "../icons";
import { LiveEventsProvider, useAttentionCounts } from "./LiveEvents";
import { OwnersOnlyPage } from "./OwnersOnlyPage";
import { SetupEntry } from "./setup/SetupEntry";
import { SetupHero } from "./setup/SetupHero";
import { ShellFrame } from "./ShellFrame";
import { SupportBanner } from "./SupportBanner";
import type { ShellNavItem } from "./types";
import { useMemberRole } from "./useMemberRole";

const SECTION_ICONS: Record<BusinessSection, ComponentType<IconProps>> = {
  overview: IconGauge,
  inbox: IconInbox,
  bookings: IconCalendar,
  assistant: IconSparkles,
  settings: IconSettings,
};

/** Settings live under "More" on phones; the other four sections are the tab bar. */
const MORE_SECTIONS: ReadonlySet<BusinessSection> = new Set(["settings"]);

export type PagePrefetch = Partial<Record<BusinessPage, () => void>>;

function useNavItems(prefetch: PagePrefetch): ShellNavItem[] {
  const { t } = useI18n();
  const { business, isPlatformAdmin } = useBusiness();
  const role = useMemberRole();
  const counts = useAttentionCounts();
  const current = businessLocation(usePathname())?.page ?? null;

  const items: ShellNavItem[] = visibleSections(role).map((section) => {
    const pages = visiblePages(section, role);
    const home = pages[0]?.page ?? section;
    return {
      key: section,
      href: businessPath(business.id, home),
      label: t(SECTION_LABELS[section]),
      icon: SECTION_ICONS[section],
      isActive: current !== null && sectionOf(current) === section,
      badge: sectionBadge(
        pages.map((entry) => entry.page),
        counts,
      ),
      onPrefetch: prefetch[home],
      inTabBar: !MORE_SECTIONS.has(section),
      pages: pages.map((entry) => ({
        href: businessPath(business.id, entry.page),
        label: t(entry.label),
        isActive: current === entry.page,
        badge: pageBadge(entry.page, counts),
        isAdvanced: entry.isAdvanced,
        onPrefetch: prefetch[entry.page],
      })),
    };
  });
  if (isPlatformAdmin) {
    items.push({ key: "admin", href: ADMIN_PATH, label: t("nav.admin"), icon: IconShield, isActive: false, secondary: true });
  }
  return items;
}

function CabinetFrame({ children, prefetch, initialCollapsed }: { children: ReactNode; prefetch: PagePrefetch; initialCollapsed: boolean }) {
  const { t } = useI18n();
  const { business, me } = useBusiness();
  const role = useMemberRole();
  const pathname = usePathname();
  const page = businessLocation(pathname)?.page ?? null;
  const items = useNavItems(prefetch);

  return (
    <ShellFrame
      items={items}
      me={me}
      initialCollapsed={initialCollapsed}
      context={business.name}
      title={page ? t(pageLabel(page)) : undefined}
      showTabBar={!isConversationPath(pathname)}
      showPhoneTopBar={!isConversationPath(pathname)}
      isWide={page === "inbox"}
      ring={(compact) => <SetupRing compact={compact} />}
      switcher={(onNavigate, compact) => (
        <BusinessSwitcher
          memberships={me.memberships ?? []}
          currentBusinessId={business.id}
          currentBusinessName={business.name}
          onNavigate={onNavigate}
          compact={compact}
        />
      )}
    >
      {page && !canOpenPage(page, role) ? (
        <OwnersOnlyPage />
      ) : (
        <>
          {/* Changes customers do not get yet; an open conversation keeps the whole phone screen. */}
          {isConversationPath(pathname) ? null : <PendingChangesBanner />}
          {/* Platform support looking in: always shown, the owner must see it. */}
          <SupportBanner />
          {children}
          <MilestoneCelebrations />
        </>
      )}
    </ShellFrame>
  );
}

function SetupFrame({ initialCollapsed }: { initialCollapsed: boolean }) {
  const { t } = useI18n();
  const { business, me, isOwner, isPlatformAdmin } = useBusiness();
  const canSetUp = isOwner || isPlatformAdmin;

  return (
    <ShellFrame
      items={[]}
      me={me}
      initialCollapsed={initialCollapsed}
      context={business.name}
      title={t("setup.navEntry")}
      showTabBar={false}
      sidebarReplacement={(collapsed) => <SetupEntry canSetUp={canSetUp} collapsed={collapsed} />}
      switcher={(onNavigate, compact) => (
        <BusinessSwitcher
          memberships={me.memberships ?? []}
          currentBusinessId={business.id}
          currentBusinessName={business.name}
          onNavigate={onNavigate}
          compact={compact}
        />
      )}
    >
      <SupportBanner />
      <SetupHero canSetUp={canSetUp} />
    </ShellFrame>
  );
}

/**
 * `prefetch` loads a page's first data while its link is under the pointer
 * or focused, so the page opens with it.
 */
export function BusinessShell({
  children,
  prefetch = {},
  initialCollapsed = false,
}: {
  children: ReactNode;
  prefetch?: PagePrefetch;
  /** The sidebar is a rail of icons (the person's choice, from a cookie). */
  initialCollapsed?: boolean;
}) {
  const { isSetUp } = useBusiness();
  // "Create an AI assistant" is full screen, before and after the launch.
  const isTunnel = businessLocation(usePathname())?.isSetup ?? false;
  return (
    <LiveEventsProvider enabled={isSetUp}>
      {isTunnel ? (
        children
      ) : isSetUp ? (
        <ApplyChangesProvider>
          <CabinetFrame prefetch={prefetch} initialCollapsed={initialCollapsed}>
            {children}
          </CabinetFrame>
        </ApplyChangesProvider>
      ) : (
        <SetupFrame initialCollapsed={initialCollapsed} />
      )}
    </LiveEventsProvider>
  );
}
