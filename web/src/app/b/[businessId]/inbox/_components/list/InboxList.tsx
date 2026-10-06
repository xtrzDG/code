"use client";

/**
 * The conversations of the chosen view: a skeleton while the first page
 * loads, a calm empty state per view, "nothing matches" for filters, and
 * "show more" for the next page. While another view loads, the previous
 * rows stay dimmed. Above the rows a bar with the density, the keyboard
 * shortcuts and, once rows are selected, "Mark resolved"; beside a row
 * resting under the pointer, its details.
 */

import { useEffect, useState } from "react";

import { IconCheck, IconChat, IconInbox, IconUsers } from "@/components/icons";
import { LoadMore, RefreshFailed } from "@/components/insights/common";
import { Button, Card, EmptyState, ErrorState, LoadingRegion, Skeleton } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";
import type { InboxView } from "@/lib/navigation";

import type { InboxDensity } from "../../_lib/inboxLayout";
import type { InboxFilters } from "../../_lib/inboxModel";
import { ARIA_KEY_SHORTCUTS } from "../../_lib/inboxShortcuts";
import { isResolvable } from "../../_lib/triage";
import type { InboxList as InboxListData } from "../../_lib/useInboxList";
import type { InboxTriage } from "../../_lib/useInboxTriage";
import type { Team } from "../../_lib/useTeam";
import { InboxRowItem } from "./InboxRowItem";
import { ListHeader } from "./ListHeader";
import { RowHint, type HintTarget } from "./RowHint";

/** Ages on the rows move on once a minute. */
const MINUTE_MS = 60_000;

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

function useMinuteClock(): number {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), MINUTE_MS);
    return () => window.clearInterval(timer);
  }, []);
  return now;
}

export function InboxList({
  list,
  filters,
  team,
  selectedId,
  linkQuery,
  hasFilters,
  density,
  onDensity,
  triage,
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
  density: InboxDensity;
  onDensity: (density: InboxDensity) => void;
  triage: InboxTriage;
  onShowAll: () => void;
  onClearFilters: () => void;
}) {
  const { t } = useI18n();
  const { rows, page } = list;
  const nowMs = useMinuteClock();
  const [hint, setHint] = useState<HintTarget | null>(null);

  if (rows === undefined) {
    return page.error ? (
      <Card className="lg:min-h-0 lg:flex-1">
        <ErrorState error={page.error} onRetry={page.reload} />
      </Card>
    ) : (
      <LoadingRegion label={t("inbox.loading")} className="lg:min-h-0 lg:flex-1">
        <InboxRowsSkeleton density={density} />
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

  const isSelecting = triage.selection.size > 0;
  const events = {
    onToggle: triage.toggle,
    onCursor: (row: { id: string }) => triage.setCursorId(row.id),
    onHint: (row: HintTarget["row"] | null, element: HTMLElement | null) => setHint(row && element ? { row, element } : null),
  };

  return (
    <>
      {page.error ? <RefreshFailed error={page.error} onRetry={page.reload} /> : null}
      <div
        data-inbox-list=""
        className={cn(
          "@container/list animate-settle overflow-hidden rounded-2xl border border-line bg-surface shadow-sm transition-opacity lg:min-h-0 lg:flex-1 lg:overflow-y-auto",
          page.isPlaceholder && "opacity-60",
        )}
        aria-busy={page.isPlaceholder || undefined}
      >
        <ListHeader
          density={density}
          onDensity={onDensity}
          selection={triage.selectionState}
          selectedCount={triage.selection.size}
          canSelect={rows.some(isResolvable)}
          isResolving={triage.isResolving}
          onToggleAll={triage.toggleAll}
          onResolve={triage.resolveSelected}
          onClear={triage.clearSelection}
          onShortcuts={triage.openSheet}
        />
        <p id="inbox-keys-hint" className="sr-only">
          {t("inboxTriage.keys.listHint")}
        </p>
        <ul
          className="divide-y divide-line"
          aria-label={t("inbox.listLabel")}
          aria-describedby="inbox-keys-hint"
          aria-keyshortcuts={ARIA_KEY_SHORTCUTS}
        >
          {rows.map((row) => (
            <InboxRowItem
              key={row.id}
              row={row}
              member={team.find(row.assigneeUserId)}
              state={{
                density,
                isOpen: row.id === selectedId,
                isCursor: row.id === triage.cursorId,
                isChecked: triage.selection.has(row.id),
                isSelectable: isResolvable(row),
                isSelecting,
                isBusy: triage.busyIds.has(row.id),
              }}
              events={events}
              linkQuery={linkQuery}
              nowMs={nowMs}
            />
          ))}
        </ul>
        <LoadMore hasMore={page.hasMore} isLoading={page.isLoadingMore} error={page.moreError} onMore={page.loadMore} />
      </div>
      <RowHint target={hint} memberOf={team.find} />
    </>
  );
}

/** Rows while the first page loads, shaped like the chosen density. */
function InboxRowsSkeleton({ rows = 8, density }: { rows?: number; density: InboxDensity }) {
  const isCompact = density === "compact";
  return (
    <div aria-hidden className="divide-y divide-line overflow-hidden rounded-2xl border border-line bg-surface">
      <div className="h-11" />
      {Array.from({ length: rows }, (_, index) => (
        <div key={index} className={cn("flex items-center gap-3", isCompact ? "px-2 py-2" : "px-3 py-2.5")}>
          <Skeleton className={cn("shrink-0 rounded-full", isCompact ? "size-7" : "size-10")} />
          <div className="min-w-0 flex-1 space-y-2">
            <div className="flex items-center justify-between gap-2">
              <Skeleton className={index % 2 === 0 ? "h-3.5 w-32" : "h-3.5 w-24"} />
              <Skeleton className="h-3 w-10" />
            </div>
            {isCompact ? null : <Skeleton className={index % 3 === 0 ? "h-3.5 w-4/5" : "h-3.5 w-3/5"} />}
          </div>
        </div>
      ))}
    </div>
  );
}
