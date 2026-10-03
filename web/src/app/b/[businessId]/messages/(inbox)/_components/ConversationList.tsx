"use client";

import Link from "next/link";

import { useBusiness, useBusinessFormat } from "@/components/business/BusinessContext";
import { IconChat } from "@/components/icons";
import { AfterHoursBadge, ConversationStatusBadge, TestBadge } from "@/components/insights/Badges";
import { CustomerName, LoadMore } from "@/components/insights/common";
import { formatRelative } from "@/components/insights/dates";
import { CHANNEL_LABELS, MESSAGE_AUTHORS } from "@/components/insights/labels";
import type { ConversationPage, ConversationSummaryView } from "@/components/insights/types";
import type { CursorPage } from "@/api/useCursorPage";
import { Button, Card, EmptyState, ErrorState, LoadingRegion, Skeleton } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";
import { languageName } from "@/lib/format";
import { businessPath } from "@/lib/navigation";

import { initialsOf } from "./conversationModel";

export function ConversationList({
  query,
  isFiltered,
  isStale,
  selectedId,
  linkQuery,
  onClearFilters,
}: {
  query: CursorPage<ConversationSummaryView, ConversationPage>;
  /** Some filter is set: an empty page means "nothing matches", not "no conversations". */
  isFiltered: boolean;
  /** The shown rows belong to the previous filters while new ones load. */
  isStale: boolean;
  selectedId: string | null;
  linkQuery: string;
  onClearFilters: () => void;
}) {
  const { t } = useI18n();
  const items = query.items;

  if (items === undefined) {
    return query.error ? (
      <Card className="lg:min-h-0 lg:flex-1">
        <ErrorState error={query.error} onRetry={query.reload} />
      </Card>
    ) : (
      <LoadingRegion label={t("conversations.loading")} className="lg:min-h-0 lg:flex-1">
        <ConversationRowsSkeleton />
      </LoadingRegion>
    );
  }

  if (items.length === 0 && !isStale && query.hasMore) {
    // A search looks at the latest conversations first; older ones on request.
    return (
      <Card>
        <EmptyState
          title={t("insights.noMatchesTitle")}
          description={t("conversations.searchOlderDescription")}
          action={
            <Button variant="secondary" onClick={query.loadMore} isLoading={query.isLoadingMore}>
              {t("conversations.searchOlder")}
            </Button>
          }
        />
      </Card>
    );
  }

  if (items.length === 0 && !isStale) {
    return (
      <Card>
        {!isFiltered ? (
          <EmptyState
            icon={<IconChat className="size-6" />}
            title={t("conversations.emptyTitle")}
            description={t("conversations.emptyDescription")}
          />
        ) : (
          <EmptyState
            title={t("insights.noMatchesTitle")}
            description={t("insights.noMatchesDescription")}
            action={
              <Button variant="secondary" onClick={onClearFilters}>
                {t("insights.clearFilters")}
              </Button>
            }
          />
        )}
      </Card>
    );
  }

  return (
    <div
      className={cn(
        "animate-settle overflow-hidden rounded-2xl border border-line bg-surface shadow-sm transition-opacity lg:min-h-0 lg:flex-1 lg:overflow-y-auto",
        isStale && "opacity-60",
      )}
      aria-busy={isStale || undefined}
    >
      <ul className="divide-y divide-line">
        {items.map((conversation) => (
          <ConversationRow
            key={conversation.id}
            conversation={conversation}
            isSelected={conversation.id === selectedId}
            linkQuery={linkQuery}
          />
        ))}
      </ul>
      <LoadMore
        hasMore={query.hasMore}
        isLoading={query.isLoadingMore}
        error={query.moreError}
        onMore={query.loadMore}
      />
    </div>
  );
}

function ConversationRow({
  conversation,
  isSelected,
  linkQuery,
}: {
  conversation: ConversationSummaryView;
  isSelected: boolean;
  linkQuery: string;
}) {
  const { t, tp, locale } = useI18n();
  const { business } = useBusiness();
  const format = useBusinessFormat();
  const href = `${businessPath(business.id, "messages")}/${encodeURIComponent(conversation.id)}${linkQuery ? `?${linkQuery}` : ""}`;
  const when = formatRelative(conversation.last_message_at, locale, { maxDays: 1 }) ?? format.date(conversation.last_message_at);

  return (
    <li>
      <Link
        href={href}
        aria-current={isSelected ? "page" : undefined}
        className={cn(
          "flex gap-3 px-4 py-3 transition-colors focus-visible:-outline-offset-2",
          isSelected ? "bg-accent-soft" : "hover:bg-surface-muted",
        )}
      >
        <span
          className="flex size-10 shrink-0 items-center justify-center rounded-full bg-surface-muted text-sm font-semibold text-ink-muted"
          aria-hidden
        >
          {initialsOf(conversation.contact_name)}
        </span>
        <span className="min-w-0 flex-1">
          <span className="flex items-baseline justify-between gap-2">
            <span className="truncate text-sm font-medium text-ink">
              {conversation.contact_name ? (
                <CustomerName name={conversation.contact_name} />
              ) : conversation.contact_phone_number ? (
                <span dir="ltr">{conversation.contact_phone_number}</span>
              ) : (
                <CustomerName name={null} />
              )}
            </span>
            <span className="shrink-0 text-xs text-ink-subtle">{when}</span>
          </span>
          {conversation.last_message_text ? (
            <span className="mt-0.5 line-clamp-2 text-sm break-words text-ink-muted">
              {conversation.last_message_author && conversation.last_message_author !== "customer" ? (
                <span className="text-ink-subtle">{t(MESSAGE_AUTHORS[conversation.last_message_author])}: </span>
              ) : null}
              <bdi>{conversation.last_message_text}</bdi>
            </span>
          ) : null}
          <span className="mt-1.5 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-ink-subtle">
            <span>
              {[
                t(CHANNEL_LABELS[conversation.channel]),
                conversation.language ? languageName(conversation.language, locale) : null,
                // A call lives in its transcript, not in messages: "0 messages" would mislead.
                conversation.channel === "phone" && conversation.customer_message_count === 0
                  ? null
                  : tp("conversations.customerMessages", conversation.customer_message_count),
              ]
                .filter(Boolean)
                .join(" · ")}
            </span>
            {conversation.status !== "closed" ? <ConversationStatusBadge status={conversation.status} /> : null}
            {conversation.is_after_hours ? <AfterHoursBadge /> : null}
            {conversation.rating ? <RatingMark rating={conversation.rating} /> : null}
            {conversation.is_sandbox ? <TestBadge /> : null}
          </span>
        </span>
      </Link>
    </li>
  );
}

function RatingMark({ rating }: { rating: NonNullable<ConversationSummaryView["rating"]> }) {
  const { t } = useI18n();
  return (
    <span
      className={cn("text-xs font-medium", rating === "good" ? "text-success" : "text-danger")}
      title={t(rating === "good" ? "conversations.rating.good" : "conversations.rating.bad")}
    >
      <span aria-hidden>{rating === "good" ? "▲" : "▼"}</span>
      <span className="sr-only">{t(rating === "good" ? "conversations.rating.good" : "conversations.rating.bad")}</span>
    </span>
  );
}

/** Feed rows while the first page loads: an avatar, a name with a time and the last message. */
export function ConversationRowsSkeleton({ rows = 6 }: { rows?: number }) {
  return (
    <div aria-hidden className="divide-y divide-line overflow-hidden rounded-2xl border border-line bg-surface">
      {Array.from({ length: rows }, (_, index) => (
        <div key={index} className="flex gap-3 px-4 py-3">
          <Skeleton className="size-10 shrink-0 rounded-full" />
          <div className="min-w-0 flex-1 space-y-2">
            <div className="flex items-center justify-between gap-2">
              <Skeleton className={index % 2 === 0 ? "h-3.5 w-32" : "h-3.5 w-24"} />
              <Skeleton className="h-3 w-10" />
            </div>
            <Skeleton className="h-3 w-full" />
            <Skeleton className={index % 3 === 0 ? "h-3 w-3/5" : "h-3 w-2/5"} />
          </div>
        </div>
      ))}
    </div>
  );
}
