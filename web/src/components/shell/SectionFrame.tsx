"use client";

/**
 * The frame of a section with pages (Messages, Assistant, Settings): the
 * section's title, what it is for, its actions and the tabs of the pages
 * the viewer's role may open (badges where something waits; the
 * Assistant's advanced page set apart at the end). The pages inside get
 * <h2> headers (SubPages). On a phone an open conversation takes the whole
 * screen, so the frame steps aside there.
 */

import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

import { useBusiness } from "@/components/business/BusinessContext";
import { SectionTabs, type SectionTab } from "@/components/content/SectionTabs";
import { IconWrench } from "@/components/icons";
import { PageHeader, SubPages } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";
import { pageBadge } from "@/lib/inboxBadges";
import { businessLocation, businessPath, isConversationPath } from "@/lib/navigation";
import { SECTION_DESCRIPTIONS, SECTION_LABELS, visiblePages, type BusinessSection } from "@/lib/sections";

import { useInboxCounts } from "./InboxCounts";
import { NavBadge } from "./NavBadge";
import { useMemberRole } from "./useMemberRole";

export function SectionFrame({
  section,
  actions,
  aside,
  children,
}: {
  section: BusinessSection;
  actions?: ReactNode;
  /** Under the title (the Assistant's live version). */
  aside?: ReactNode;
  children: ReactNode;
}) {
  const { t } = useI18n();
  const { business } = useBusiness();
  const role = useMemberRole();
  const counts = useInboxCounts();
  const pathname = usePathname();
  const location = businessLocation(pathname);
  const label = t(SECTION_LABELS[section]);
  const isConversationOpen = isConversationPath(pathname);

  const tabs: SectionTab[] = visiblePages(section, role).map((entry) => ({
    href: businessPath(business.id, entry.page),
    isApart: entry.isAdvanced,
    title: entry.isAdvanced ? t(entry.label) : undefined,
    label: entry.isAdvanced ? (
      <>
        <IconWrench className="size-4" aria-hidden />
        <span>{t("navigation.advanced")}</span>
        <span className="sr-only">: {t(entry.label)}</span>
      </>
    ) : (
      <>
        <span>{t(entry.label)}</span>
        <NavBadge count={pageBadge(entry.page, counts)} size="sm" />
      </>
    ),
  }));

  return (
    <>
      <div className={cn(isConversationOpen && "hidden lg:block")}>
        <PageHeader title={label} description={t(SECTION_DESCRIPTIONS[section])} actions={actions} className="sm:mb-6" />
        {aside}
        {tabs.length > 1 ? (
          <SectionTabs
            label={t("navigation.sectionPages", { section: label })}
            tabs={tabs}
            activeHref={location?.page ? businessPath(business.id, location.page) : undefined}
          />
        ) : null}
      </div>
      {isConversationOpen ? <h1 className="sr-only lg:hidden">{label}</h1> : null}
      <SubPages>{children}</SubPages>
    </>
  );
}
