"use client";

import Link from "next/link";

import type { CursorPage } from "@/api/useCursorPage";
import { useBusiness, useBusinessFormat } from "@/components/business/BusinessContext";
import { IconSend } from "@/components/icons";
import { ChannelBadge } from "@/components/insights/Badges";
import { LoadMore } from "@/components/insights/common";
import { Badge, Card, EmptyState, ErrorState, SkeletonRows } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { conversationPath } from "@/lib/navigation";

import {
  MESSAGE_STATUS_LABELS,
  MESSAGE_STATUS_TONES,
  RULE_LABELS,
  SKIP_REASON_LABELS,
  type CampaignMessage,
  type CampaignMessagePage,
} from "../_lib/returnVisitsModel";

/** The latest messages: who got one (or why not), and who booked again after it. */
export function CampaignMessagesCard({ messages }: { messages: CursorPage<CampaignMessage, CampaignMessagePage> }) {
  const { t } = useI18n();
  const items = messages.items ?? [];
  return (
    <Card title={t("returnVisits.messages.title")} description={t("returnVisits.messages.description")} padded={items.length === 0}>
      {messages.error && !messages.items ? (
        <ErrorState error={messages.error} onRetry={messages.reload} className="py-6" />
      ) : !messages.items ? (
        <SkeletonRows rows={3} />
      ) : items.length === 0 ? (
        <EmptyState
          className="py-6"
          icon={<IconSend className="size-6" />}
          title={t("returnVisits.messages.empty")}
          description={t("returnVisits.messages.emptyDescription")}
        />
      ) : (
        <>
          <ul className="divide-y divide-line">
            {items.map((item) => (
              <MessageRow key={item.id} item={item} />
            ))}
          </ul>
          <div className="px-4 pb-4 sm:px-6">
            <LoadMore hasMore={messages.hasMore} isLoading={messages.isLoadingMore} error={messages.moreError} onMore={messages.loadMore} />
          </div>
        </>
      )}
    </Card>
  );
}

function MessageRow({ item }: { item: CampaignMessage }) {
  const { t } = useI18n();
  const format = useBusinessFormat();
  const { business } = useBusiness();
  return (
    <li className="flex flex-col gap-2 px-4 py-3 sm:flex-row sm:items-start sm:justify-between sm:px-6">
      <div className="min-w-0 space-y-0.5">
        <p className="text-sm font-medium text-ink [overflow-wrap:anywhere]">{item.contact_name ?? t("returnVisits.messages.customer")}</p>
        <p className="text-sm text-ink-muted">{t(RULE_LABELS[item.rule_kind])}</p>
        {item.status === "skipped" && item.skip_reason ? (
          <p className="text-sm text-ink-muted">
            {t("returnVisits.messages.notSentBecause", { reason: t(SKIP_REASON_LABELS[item.skip_reason]) })}
          </p>
        ) : item.sent_at ? (
          <p className="text-xs text-ink-subtle">{t("returnVisits.messages.sentAt", { time: format.dateTime(item.sent_at) })}</p>
        ) : null}
        {item.status === "booked" && item.booked_at ? (
          <p className="text-xs text-ink-subtle">{t("returnVisits.messages.bookedAt", { time: format.dateTime(item.booked_at) })}</p>
        ) : null}
      </div>
      <div className="flex shrink-0 flex-wrap items-center gap-2 sm:justify-end">
        <Badge tone={MESSAGE_STATUS_TONES[item.status]}>{t(MESSAGE_STATUS_LABELS[item.status])}</Badge>
        {item.channel ? <ChannelBadge channel={item.channel} /> : null}
        {item.conversation_id ? (
          <Link
            href={conversationPath(business.id, item.conversation_id)}
            className="text-sm font-medium text-accent underline underline-offset-2 hover:no-underline"
          >
            {t("returnVisits.messages.openConversation")}
          </Link>
        ) : null}
      </div>
    </li>
  );
}
