"use client";

import Link from "next/link";
import { useState } from "react";

import type { ApiQuery } from "@/api/hooks";
import { useBusiness, useBusinessFormat } from "@/components/business/BusinessContext";
import { IconChat } from "@/components/icons";
import { ConversationStatusBadge, TestBadge } from "@/components/insights/Badges";
import { CustomerName, ShowMore } from "@/components/insights/common";
import { formatRelative } from "@/components/insights/dates";
import { CHANNEL_LABELS } from "@/components/insights/labels";
import { takePage } from "@/components/insights/numbers";
import type { ConversationSummaryView } from "@/components/insights/types";
import { Button, Card, EmptyState, ErrorState, LoadingBlock } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";
import { languageName } from "@/lib/format";
import { businessPath } from "@/lib/navigation";

import { initialsOf } from "./conversationModel";

const PAGE_SIZE = 30;

export function ConversationList({
  query,
  items,
  totalLoaded,
  selectedId,
  linkQuery,
  onClearFilters,
}: {
  query: ApiQuery<ConversationSummaryView[]>;
  items: ConversationSummaryView[];
  totalLoaded: number;
  selectedId: string | null;
  linkQuery: string;
  onClearFilters: () => void;
}) {
  const { t } = useI18n();
  const [pages, setPages] = useState(1);

  if (query.data === undefined) {
    return (
      <Card className="lg:min-h-0 lg:flex-1">
        {query.error ? (
          <ErrorState error={query.error} onRetry={query.reload} />
        ) : (
          <LoadingBlock label={t("conversations.loading")} />
        )}
      </Card>
    );
  }

  if (items.length === 0) {
    return (
      <Card>
        {totalLoaded === 0 ? (
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

  const { visible } = takePage(items, pages, PAGE_SIZE);
  return (
    <div className="overflow-hidden rounded-2xl border border-line bg-surface shadow-sm lg:min-h-0 lg:flex-1 lg:overflow-y-auto">
      <ul className="divide-y divide-line">
        {visible.map((conversation) => (
          <ConversationRow
            key={conversation.id}
            conversation={conversation}
            isSelected={conversation.id === selectedId}
            linkQuery={linkQuery}
          />
        ))}
      </ul>
      {items.length > PAGE_SIZE ? (
        <ShowMore shown={visible.length} total={items.length} onMore={() => setPages((value) => value + 1)} />
      ) : null}
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
  const href = `${businessPath(business.id, "conversations")}/${encodeURIComponent(conversation.id)}${linkQuery ? `?${linkQuery}` : ""}`;
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
            <span dir="auto" className="mt-0.5 line-clamp-2 text-sm break-words text-ink-muted">
              {conversation.last_message_text}
            </span>
          ) : null}
          <span className="mt-1.5 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-ink-subtle">
            <span>
              {[
                t(CHANNEL_LABELS[conversation.channel]),
                conversation.language ? languageName(conversation.language, locale) : null,
                tp("conversations.messages", conversation.message_count),
              ]
                .filter(Boolean)
                .join(" · ")}
            </span>
            {conversation.status !== "closed" ? <ConversationStatusBadge status={conversation.status} /> : null}
            {conversation.is_sandbox ? <TestBadge /> : null}
          </span>
        </span>
      </Link>
    </li>
  );
}
