"use client";

import { useState } from "react";

import { useBusiness } from "@/components/business/BusinessContext";
import { IconClock } from "@/components/icons";
import { LoadMore, RefreshFailed } from "@/components/insights/common";
import { SegmentedControl } from "@/components/insights/SegmentedControl";
import { replaceUrlQuery } from "@/components/insights/urlQuery";
import { AnimatedPresenceList } from "@/components/motion";
import { ConfirmDialog, EmptyState, ErrorState, PageHeader, SkeletonCard, SkeletonCardList, useToast } from "@/components/ui";
import { LiveStatus } from "@/components/shell/LiveStatus";
import { useI18n } from "@/i18n/client";
import { timeZoneLabel } from "@/lib/timeZones";

import { WaitlistEntryCard } from "./_components/WaitlistEntryCard";
import { WaitlistSettingsCard } from "./_components/WaitlistSettingsCard";
import { useWaitlist } from "./_lib/useWaitlist";
import { EMPTY_TEXTS, filterCounts, WAITLIST_FILTERS, type WaitlistEntry, type WaitlistFilter } from "./_lib/waitlistModel";

const FILTER_LABELS = {
  active: "waitlist.filters.active",
  booked: "waitlist.filters.booked",
  ended: "waitlist.filters.ended",
} as const;

/**
 * Bookings → Waitlist: the customers who wait for a full day to free up
 * (a place held for one of them counts down), those who got a place, and
 * the entries that ended; staff take someone off the list, owners choose
 * whether the assistant offers the waitlist and how long a place is held.
 */
export function WaitlistScreen({ initialFilter }: { initialFilter: WaitlistFilter }) {
  const { t, locale } = useI18n();
  const toast = useToast();
  const { business, isOwner } = useBusiness();
  const [filter, setFilter] = useState<WaitlistFilter>(initialFilter);
  const [removing, setRemoving] = useState<WaitlistEntry | null>(null);
  const state = useWaitlist(filter);
  const { entries, settings, remove } = state;
  const counts = settings.data ? filterCounts(settings.data.counts ?? []) : null;
  const items = entries.items ?? [];
  const empty = EMPTY_TEXTS[filter];

  const choose = (value: WaitlistFilter) => {
    setFilter(value);
    replaceUrlQuery(value === "active" ? "" : `filter=${value}`);
  };

  const onRemove = async () => {
    if (!removing) {
      return;
    }
    const result = await remove.run(removing);
    if (result.ok) {
      setRemoving(null);
      toast.success(t("waitlist.removed"));
    }
  };

  return (
    <>
      <PageHeader
        title={t("navigation.pages.bookingsWaitlist")}
        description={t("navigation.descriptions.bookingsWaitlist")}
        status={<LiveStatus updatedAt={entries.updatedAt} isFetching={entries.isFetching && entries.items !== undefined} />}
      />
      <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_20rem]">
        <section aria-label={t("navigation.pages.bookingsWaitlist")} className="min-w-0 space-y-4">
          <SegmentedControl
            label={t("waitlist.filters.label")}
            value={filter}
            onChange={choose}
            options={WAITLIST_FILTERS.map((value) => ({ value, label: t(FILTER_LABELS[value]), count: counts?.[value] }))}
          />
          <p className="text-xs text-ink-subtle">{t("waitlist.timeZone", { timezone: timeZoneLabel(business.timezone, locale) })}</p>
          {entries.error && entries.items ? <RefreshFailed error={entries.error} onRetry={entries.reload} /> : null}
          {entries.error && !entries.items ? (
            <ErrorState error={entries.error} onRetry={entries.reload} className="py-6" />
          ) : !entries.items ? (
            <SkeletonCardList cards={3} />
          ) : items.length === 0 && !entries.isPlaceholder ? (
            <EmptyState icon={<IconClock className="size-6" />} title={t(empty.title)} description={t(empty.description)} />
          ) : (
            <AnimatedPresenceList
              items={items}
              getKey={(entry) => entry.id}
              className={entries.isPlaceholder ? "animate-settle space-y-3 opacity-60 transition-opacity" : "animate-settle space-y-3 transition-opacity"}
              renderItem={(entry) => <WaitlistEntryCard entry={entry} onRemove={setRemoving} />}
            />
          )}
          <LoadMore hasMore={entries.hasMore} isLoading={entries.isLoadingMore} error={entries.moreError} onMore={entries.loadMore} />
        </section>
        {settings.data ? (
          <WaitlistSettingsCard key={`${settings.data.is_enabled}-${settings.data.hold_minutes}`} stored={settings.data} state={state} canEdit={isOwner} />
        ) : settings.error ? (
          <ErrorState error={settings.error} onRetry={settings.reload} className="py-6" />
        ) : (
          <SkeletonCard lines={4} />
        )}
      </div>

      <ConfirmDialog
        open={removing !== null}
        onClose={() => setRemoving(null)}
        onConfirm={onRemove}
        isPending={remove.isPending}
        error={remove.error}
        title={removing ? t("waitlist.removeTitle", { name: removing.contact_name ?? t("waitlist.customer") }) : ""}
        confirmLabel={t("waitlist.removeConfirm")}
      >
        <p>{t("waitlist.removeBody")}</p>
      </ConfirmDialog>
    </>
  );
}
