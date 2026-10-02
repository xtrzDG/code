"use client";

import { useMemo } from "react";

import { sectionQueries } from "@/api/sectionQueries";
import { prefetchCursorPage } from "@/api/useCursorPage";
import { prefetchQuery } from "@/api/useQuery";
import { useBusiness } from "@/components/business/BusinessContext";
import { todayIn } from "@/components/insights/dates";
import { useI18n } from "@/i18n/client";
import type { BusinessPage } from "@/lib/navigation";

import { DEFAULT_DASHBOARD_PERIOD, periodRange } from "../overview/_components/dashboardModel";

/**
 * What each section loads first, for the sidebar to fetch while the pointer
 * or the focus is on its link. Lists of personal data (conversations,
 * bookings, leads, handoffs) are left out: every load of them is written to
 * the audit log, and a hover is not a view. Forms that save with a revision
 * (settings, the profile wizard) always load fresh, so they are left out too.
 */
export function useSectionPrefetch(): Partial<Record<BusinessPage, () => void>> {
  const { business, isOwner } = useBusiness();
  const { locale } = useI18n();
  const businessId = business.id;
  const timeZone = business.timezone;

  return useMemo(() => {
    const versions = sectionQueries.assistantVersions(businessId);
    const channels = sectionQueries.channels(businessId);
    const billing = sectionQueries.billingOverview(businessId, locale);
    return {
      overview: () => {
        const range = periodRange(DEFAULT_DASHBOARD_PERIOD, todayIn(timeZone));
        const stats = sectionQueries.dashboardStats(businessId, range.from, range.to);
        void prefetchQuery(stats.key, stats.fetch);
      },
      "assistant/knowledge": () => {
        const items = sectionQueries.knowledgeItems(businessId, locale, "all", "all");
        void prefetchCursorPage(items.key, items.fetchPage, { pageSize: items.pageSize });
      },
      assistant: () => void prefetchQuery(versions.key, versions.fetch),
      "assistant/channels": () => void prefetchQuery(channels.key, channels.fetch),
      // Staff may not read billing: no request that is bound to be refused.
      ...(isOwner ? { "settings/billing": () => void prefetchQuery(billing.key, billing.fetch) } : {}),
    };
  }, [businessId, timeZone, locale, isOwner]);
}
