"use client";

/**
 * The conversations of the chosen view: a skeleton while the first page
 * loads, a calm empty state per view, "nothing matches" for filters, and
 * "show more" for the next page. While another view loads, the previous
 * rows stay dimmed.
 */

import { IconCheck, IconChat, IconInbox, IconUsers } from "@/components/icons";
import { LoadMore, RefreshFailed } from "@/components/insights/common";
import { Button, Card, EmptyState, ErrorState, LoadingRegion, Skeleton } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";
import type { InboxView } from "@/lib/navigation";

import type { InboxFilters } from "../../_lib/inboxModel";
import type { InboxList as InboxListData } from "../../_lib/useInboxList";
import type { Team } from "../../_lib/useTeam";
import { InboxRowItem } from "./InboxRowItem";

const EMPTY_ICONS: Record<InboxView, typeof IconChat> = {
  needs_person: IconCheck,
  requests: IconInbox,
  mine: IconUsers,
  unassigned: IconCheck,
  all: IconChat,
};

function EmptyView({ view, onShowAll }: { view: InboxView; onShowAll: () => void }) {
  const { t } = useI18n();
  const Icon = EMPTY_ICONS[view];
  return (
    <Card>
      <EmptyState
        icon={<Icon className="size-6" />}
        title={t(`inbox.empty.${view}.title`)}
        description={t(`inbox.empty.${view}.description`)}
        action={
          view === "all" ? undefined : (
            <Button variant="secondary" onClick={onShowAll}>
              {t("inbox.showAll")}
            </Button>
          )
        }
      />
    </Card>
  );
}

export function InboxList({
  list,
  filters,
  team,
  selectedId,
  linkQuery,
  hasFilters,
  onShowAll,
  onClearFilters,
}: {
  list: InboxListData;
  filters: InboxFilters;
  team: Team;
  selectedId: string | null;
  linkQuery: string;
  /** A channel or another filter is set: an empty page means "nothing matches". */
  hasFilters: boolean;
  onShowAll: () => void;
  onClearFilters: () => void;
}) {
  const { t } = useI18n();
  const { rows, page } = list;

  if (rows === undefined) {
    return page.error ? (
      <Card className="lg:min-h-0 lg:flex-1">
        <ErrorState error={page.error} onRetry={page.reload} />
      </Card>
    ) : (
      <LoadingRegion label={t("inbox.loading")} className="lg:min-h-0 lg:flex-1">
        <InboxRowsSkeleton />
      </LoadingRegion>
    );
  }

  if (rows.length === 0 && !page.isPlaceholder) {
    if (list.isFeed && page.hasMore) {
      // A search looks at the latest conversations first; older ones on request.
      return (
        <Card>
          <EmptyState
            title={t("insights.noMatchesTitle")}
            description={t("conversations.searchOlderDescription")}
            action={
              <Button variant="secondary" onClick={page.loadMore} isLoading={page.isLoadingMore}>
                {t("conversations.searchOlder")}
              </Button>
            }
          />
        </Card>
      );
    }
    if (hasFilters) {
      return (
        <Card>
          <EmptyState
            title={t("insights.noMatchesTitle")}
            description={t("insights.noMatchesDescription")}
            action={
              <Button variant="secondary" onClick={onClearFilters}>
                {t("inbox.filters.clear")}
              </Button>
            }
          />
        </Card>
      );
    }
    return <EmptyView view={filters.view} onShowAll={onShowAll} />;
  }

  return (
    <>
      {page.error ? <RefreshFailed error={page.error} onRetry={page.reload} /> : null}
      <div
        className={cn(
          "animate-settle overflow-hidden rounded-2xl border border-line bg-surface shadow-sm transition-opacity lg:min-h-0 lg:flex-1 lg:overflow-y-auto",
          page.isPlaceholder && "opacity-60",
        )}
        aria-busy={page.isPlaceholder || undefined}
      >
        <ul className="divide-y divide-line" aria-label={t("inbox.listLabel")}>
          {rows.map((row) => (
            <InboxRowItem
              key={row.id}
              row={row}
              member={team.find(row.assigneeUserId)}
              isSelected={row.id === selectedId}
              linkQuery={linkQuery}
            />
          ))}
        </ul>
        <LoadMore hasMore={page.hasMore} isLoading={page.isLoadingMore} error={page.moreError} onMore={page.loadMore} />
      </div>
    </>
  );
}

/** Rows while the first page loads: an avatar, a name with a time and the last message. */
export function InboxRowsSkeleton({ rows = 6 }: { rows?: number }) {
  return (
    <div aria-hidden className="divide-y divide-line overflow-hidden rounded-2xl border border-line bg-surface">
      {Array.from({ length: rows }, (_, index) => (
        <div key={index} className="flex gap-3 px-4 py-3.5">
          <Skeleton className="size-10 shrink-0 rounded-full" />
          <div className="min-w-0 flex-1 space-y-2">
            <div className="flex items-center justify-between gap-2">
              <Skeleton className={index % 2 === 0 ? "h-3.5 w-32" : "h-3.5 w-24"} />
              <Skeleton className="h-3 w-10" />
            </div>
            <Skeleton className="h-3 w-full" />
            <Skeleton className={index % 3 === 0 ? "h-4 w-3/5 rounded-full" : "h-4 w-2/5 rounded-full"} />
          </div>
        </div>
      ))}
    </div>
  );
}
