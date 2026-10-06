"use client";

import { useBusiness } from "@/components/business/BusinessContext";
import { ErrorState, LoadingRegion, PageHeader, SkeletonCard } from "@/components/ui";
import { OwnerOnlyState } from "@/components/workspace/OwnerOnly";
import { useI18n } from "@/i18n/client";

import { CampaignMessagesCard } from "./_components/CampaignMessagesCard";
import { CampaignPreviewCard } from "./_components/CampaignPreviewCard";
import { RecentCampaignCounts } from "./_components/RecentCampaignCounts";
import { ReturnVisitsFormCard } from "./_components/ReturnVisitsFormCard";
import { useReturnVisits } from "./_lib/useReturnVisits";

/**
 * Bookings → Return visits (owners): one opt-in message that brings
 * customers back (an invitation after a visit, a reminder that a check is
 * due, a note before arrival), the last 30 days in numbers, what customers
 * read in each language and the latest messages with who booked again.
 */
export function ReturnVisitsScreen() {
  const { t } = useI18n();
  const { isOwner } = useBusiness();
  const state = useReturnVisits(isOwner);
  const { settings } = state;
  const header = (
    <PageHeader title={t("navigation.pages.bookingsReturnVisits")} description={t("navigation.descriptions.bookingsReturnVisits")} />
  );

  if (!isOwner || settings.error?.code === "access_denied") {
    return (
      <>
        <PageHeader title={t("navigation.pages.bookingsReturnVisits")} />
        <OwnerOnlyState />
      </>
    );
  }

  if (settings.error && !settings.data) {
    return (
      <>
        {header}
        <ErrorState error={settings.error} onRetry={settings.reload} className="py-6" />
      </>
    );
  }

  if (!settings.data) {
    return (
      <>
        {header}
        <LoadingRegion label={t("returnVisits.loading")} className="space-y-6">
          <SkeletonCard lines={6} />
          <SkeletonCard lines={3} />
        </LoadingRegion>
      </>
    );
  }

  return (
    <>
      {header}
      <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_22rem]">
        <div className="min-w-0 space-y-6">
          <ReturnVisitsFormCard stored={settings.data} state={state} />
          <CampaignMessagesCard messages={state.messages} />
        </div>
        <div className="min-w-0 space-y-6">
          <RecentCampaignCounts view={settings.data} />
          <CampaignPreviewCard previews={settings.data.previews} />
        </div>
      </div>
    </>
  );
}
